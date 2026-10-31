"""Live, read-only access to administrator-configured analytical PostgreSQL tables."""
from contextlib import contextmanager
import json

import pandas as pd
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.engine import make_url
from sqlalchemy.exc import SQLAlchemyError

from app.config import settings


@contextmanager
def connection(name):
    dsn = settings.ANALYTICS_CONNECTIONS.get(name)
    if not dsn:
        raise ValueError("Выберите настроенное аналитическое подключение")
    url = make_url(dsn)
    if url.get_backend_name() != "postgresql":
        raise ValueError("Поддерживается PostgreSQL")
    engine = create_engine(url, connect_args={"connect_timeout": 10}, pool_pre_ping=True)
    try:
        with engine.connect() as conn, conn.begin():
            conn.execute(text("SET TRANSACTION READ ONLY"))
            conn.execute(text("SELECT set_config('statement_timeout', :timeout, true)"),
                         {"timeout": str(settings.ANALYTICS_TIMEOUT_MS)})
            yield conn
    except SQLAlchemyError as exc:
        # Driver messages can contain credentials, hosts or SQL; keep them server-side.
        raise ValueError("Не удалось прочитать аналитическую БД. Проверьте подключение, права и доступность таблицы.") from exc
    finally:
        engine.dispose()


def list_tables(name):
    with connection(name) as conn:
        inspector = inspect(conn)
        return [{"schema": schema, "table": table}
                for schema in inspector.get_schema_names() if schema not in {"pg_catalog", "information_schema"}
                for table in sorted(set(inspector.get_table_names(schema) + inspector.get_view_names(schema)))]


def read_table(descriptor):
    with connection(descriptor["connection_id"]) as conn:
        schema, table = descriptor["schema"], descriptor["table"]
        if not schema or not table or "\x00" in schema + table:
            raise ValueError("Укажите схему и таблицу")
        quote = conn.dialect.identifier_preparer.quote_identifier
        query = text(f"SELECT * FROM {quote(schema)}.{quote(table)} LIMIT :limit")
        df = pd.read_sql_query(query, conn, params={"limit": settings.MAX_FILE_ROWS + 1})
        if len(df) > settings.MAX_FILE_ROWS:
            raise ValueError("Таблица превышает лимит строк. Подключите представление с нужным срезом данных.")
        inspector = inspect(conn)
        keys = inspector.get_pk_constraint(table, schema).get("constrained_columns", []) or []
        descriptions = {c["name"]: c["comment"] for c in inspector.get_columns(table, schema) if c.get("comment")}
    technical_id = "_row_id"
    while technical_id in df.columns:
        technical_id = "_" + technical_id
    df.insert(0, technical_id, range(1, len(df) + 1))
    structured = []
    for column in df.columns:
        if df[column].map(lambda value: isinstance(value, (dict, list))).any():
            df[column] = df[column].map(lambda value: json.dumps(value, ensure_ascii=False, sort_keys=True, default=str)
                                       if isinstance(value, (dict, list)) else value)
            structured.append(column)
    df.attrs.update(key_columns=keys, column_descriptions=descriptions, technical_id_column=technical_id,
                    warnings=["Данные прочитаны напрямую из PostgreSQL; следующий запрос может увидеть обновления таблицы."])
    if structured:
        df.attrs["warnings"].append("JSON и массивы представлены текстом для анализа: " + ", ".join(structured))
    return df
