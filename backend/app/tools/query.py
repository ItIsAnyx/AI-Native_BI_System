"""Read-only analytical SQL over one explicitly registered source, with bounded resources."""
from decimal import Decimal
import threading
import time

import duckdb
import numpy as np
import pandas as pd

from app.config import settings
from app.services.cancellation import checkpoint, current
from app.tools.preprocessing import _rows, _validate


def query_dataset(df: pd.DataFrame, sql: str, limit: int = 100) -> dict:
    _validate(df, limit)
    if not isinstance(sql, str) or not sql.strip() or len(sql) > 30000:
        raise ValueError("Укажите один аналитический SELECT-запрос длиной до 30000 символов")
    checkpoint()
    connection = duckdb.connect(database=":memory:", config={
        "enable_external_access": False, "autoinstall_known_extensions": False,
        "autoload_known_extensions": False, "allow_unsigned_extensions": False,
        "allow_community_extensions": False, "python_enable_replacements": False,
        "threads": 2, "memory_limit": f"{settings.QUERY_MEMORY_MB}MB", "max_temp_directory_size": "0B",
    })
    done = threading.Event()
    timed_out = threading.Event()
    operation = current.get()
    deadline = time.monotonic() + settings.QUERY_TIMEOUT_SECONDS
    def watch():
        while not done.wait(.05):
            if operation is not None and operation.stop.is_set():
                connection.interrupt()
                return
            if time.monotonic() >= deadline:
                timed_out.set()
                connection.interrupt()
                return
    watcher = None
    try:
        connection.execute("SET lock_configuration=true")
        connection.register("dataset", df)
        statements = connection.extract_statements(sql)
        if len(statements) != 1 or statements[0].type != duckdb.StatementType.SELECT:
            raise ValueError("Разрешён только один SELECT или WITH…SELECT; изменение данных и настройки недоступны")
        # Unknown Python variables must never become implicitly accessible tables.
        unknown = connection.get_table_names(statements[0].query) - {"dataset"}
        if unknown:
            raise ValueError("Недоступные таблицы: " + ", ".join(sorted(unknown)) + ". Используйте dataset текущего source_id")
        checkpoint()
        watcher = threading.Thread(target=watch, daemon=True)
        watcher.start()
        cursor = connection.execute(statements[0].query)
        names = [column[0] for column in cursor.description]
        if len(names) > 100 or len(set(names)) != len(names):
            raise ValueError("Результат должен содержать до 100 столбцов с уникальными названиями")
        maximum = min(settings.QUERY_MAX_ROWS, settings.MAX_FILE_ROWS)
        records = cursor.fetchmany(maximum + 1)
        checkpoint()
        if len(records) > maximum:
            raise ValueError(f"Результат превышает {maximum} строк. Добавьте группировку или явный LIMIT; данные не обрезаны молча")
        result = pd.DataFrame.from_records(records, columns=names)
        for name in names:
            if result[name].map(lambda value: isinstance(value, Decimal)).any():
                result[name] = pd.to_numeric(result[name])
            if pd.api.types.is_numeric_dtype(result[name]) and not np.isfinite(result[name].dropna()).all():
                raise ValueError("Расчёт дал бесконечность или NaN; используйте NULLIF для нулевого знаменателя")
        result.attrs = {"warnings": [], "key_columns": [key for key in df.attrs.get("key_columns", []) if key in names],
                        "technical_id_column": df.attrs.get("technical_id_column") if df.attrs.get("technical_id_column") in names else None}
        return {"operation": "query_dataset", "sql": statements[0].query,
                "input_rows": len(df), "total_rows": len(result), "columns": names,
                "rows": _rows(result.head(limit)), "returned_count": min(limit, len(result)),
                "truncated": len(result) > limit, "limit": limit,
                "source_warnings": list(df.attrs.get("warnings", [])), "_dataframe": result}
    except duckdb.InterruptException as exc:
        checkpoint()
        raise ValueError("Время расчёта превышено. Сузьте период или упростите запрос") from exc
    except duckdb.Error as exc:
        checkpoint()
        message = str(exc)
        hint = ("Разность дат имеет тип INTERVAL. Для числовых часов используйте epoch(конец-начало)/3600.0; "
                "в quantile_cont передавайте числовую длительность. " if "INTERVAL" in message else "")
        raise ValueError("Не удалось выполнить аналитический запрос: " + hint + message[:700]) from exc
    finally:
        done.set()
        if watcher is not None:
            watcher.join()
        connection.close()


QUERY_TOOL = {"type": "function", "function": {
    "name": "query_dataset",
    "description": "Рассчитать сложную аналитику по ВСЕМ строкам CSV или PostgreSQL-источника через один DuckDB SELECT над таблицей dataset. Поддерживает WITH, арифметику, даты, условные агрегаты, оконные функции, P90/P95, календарные знаменатели и цепочки попыток. Столбцы с пробелами/кириллицей заключай в двойные кавычки. Не используй пути, read_csv, сеть, Python, CREATE, COPY, PRAGMA или несколько запросов. Результат сохраняется новым CSV для графиков и продолжения диалога; исходник сохраняется. Числа результата выводит приложение. Назови столбцы результата понятно пользователю и включи компоненты расчёта: базы, суммы, количества, знаменатели и процент. limit ограничивает только показ строк.",
    "parameters": {"type": "object", "properties": {
        "sql": {"type": "string", "minLength": 1, "maxLength": 30000,
                "description": "Один DuckDB SELECT/WITH…SELECT. Исходная таблица называется строго dataset, а не именем файла, источника или source_id. Пример: SELECT \"Группа\", COUNT(*) AS n, quantile_cont(\"Часы\",0.9) AS p90 FROM dataset GROUP BY \"Группа\" HAVING COUNT(*)>=100 ORDER BY p90 DESC LIMIT 1. Есть TRY_CAST(column AS TIMESTAMP), greatest(delay,0), NULLIF для нулевого знаменателя."},
        "limit": {"type": "integer", "minimum": 1, "maximum": 1000, "default": 100},
    }, "required": ["sql"], "additionalProperties": False},
}}
