import re

import pandas as pd
from app.tools.column_values import _json_value
from app.tools.errors import DataSelectionError


JOIN_TYPES = ("left", "inner", "right", "outer")
JOIN_RELATIONSHIPS = ("one_to_one", "one_to_many", "many_to_one", "many_to_many")
MAX_JOIN_ROWS = 100000


def join_source_ids(source_id: str, joins: list[dict]) -> list[str]:
    if not isinstance(source_id, str) or not source_id:
        raise ValueError("Укажите source_id основной таблицы из list_sources")
    if not isinstance(joins, list) or not 1 <= len(joins) <= 9:
        raise ValueError("Укажите от 1 до 9 соединений таблиц")
    source_ids = [source_id]
    aliases = {"base"}
    for step in joins:
        if not isinstance(step, dict) or set(step) - {"source_id", "alias", "left_on", "right_on", "how", "relationship"}:
            raise ValueError("Некорректные параметры соединения")
        other_id = step.get("source_id")
        if not isinstance(other_id, str) or not other_id:
            raise ValueError("Для каждого соединения укажите source_id из list_sources")
        alias = step.get("alias")
        if not isinstance(alias, str) or not re.fullmatch(r"[A-Za-z][A-Za-z0-9_]{0,31}", alias) or alias in aliases:
            raise ValueError("alias должен быть уникальным именем из латинских букв, цифр и _, начиная с буквы; base зарезервирован")
        aliases.add(alias)
        for name in ("left_on", "right_on"):
            keys = step.get(name)
            if not isinstance(keys, list) or not keys or any(not isinstance(key, str) or not key for key in keys):
                raise ValueError(f"{name} должен быть непустым списком названий столбцов")
            if len(set(keys)) != len(keys):
                raise ValueError(f"Столбцы в {name} не должны повторяться")
        if len(step["left_on"]) != len(step["right_on"]):
            raise ValueError("Число ключей left_on и right_on должно совпадать")
        if step.get("how", "left") not in JOIN_TYPES:
            raise ValueError("how должен быть left, inner, right или outer")
        if step.get("relationship", "many_to_one") not in JOIN_RELATIONSHIPS:
            raise ValueError("Укажите допустимый тип связи relationship")
        source_ids.append(other_id)
    return list(dict.fromkeys(source_ids))


def _key_type(values: pd.Series) -> str:
    kind = pd.api.types.infer_dtype(values.dropna(), skipna=True)
    if kind in ("integer", "floating", "mixed-integer-float", "decimal", "complex"):
        return "numeric"
    if kind in ("string", "unicode", "bytes"):
        return "string"
    return kind


def _table(dataframes: dict, source_id: str, alias: str):
    df = dataframes.get(source_id)
    if not isinstance(df, pd.DataFrame):
        raise ValueError(f"Таблица источника {source_id!r} недоступна")
    if not df.columns.is_unique or any(not isinstance(column, str) for column in df.columns):
        raise ValueError("Названия столбцов должны быть уникальными строками")
    columns = [{"name": f"{alias}.{column}", "source_id": source_id, "column": column} for column in df.columns]
    # Object columns retain large integer IDs when an outer join introduces nulls.
    return df.astype(object).rename(columns={column: f"{alias}.{column}" for column in df.columns}), columns


def join_tables(dataframes: dict[str, pd.DataFrame], source_id: str, joins: list[dict], limit: int = 10) -> dict:
    join_source_ids(source_id, joins)
    if type(limit) is not int or not 1 <= limit <= 1000:
        raise ValueError("Количество результатов должно быть целым числом от 1 до 1000")
    if not isinstance(dataframes, dict):
        raise TypeError("Нужно передать словарь таблиц pandas.DataFrame")
    result, columns = _table(dataframes, source_id, "base")
    steps = []
    warnings = []
    for step in joins:
        right, right_columns = _table(dataframes, step["source_id"], step["alias"])
        left_on = []
        for key in step["left_on"]:
            if key not in result.columns and "." not in key:
                matches = [name for name in result.columns if name.split(".", 1)[1] == key]
                if len(matches) > 1:
                    raise DataSelectionError(f"Ключ «{key}» неоднозначен: {', '.join(matches)}. Укажите префикс таблицы")
                if len(matches) == 1:
                    warnings.append(f"Ключ «{key}» однозначно соответствует «{matches[0]}»")
                    key = matches[0]
            left_on.append(key)
        if len(set(left_on)) != len(left_on):
            raise ValueError("Ключи left_on повторяются после уточнения префиксов")
        right_on = [f"{step['alias']}.{column}" for column in step["right_on"]]
        for table, keys in ((result, left_on), (right, right_on)):
            for key in keys:
                if key not in table.columns:
                    available = ", ".join(str(column) for column in table.columns)
                    raise ValueError(f"Столбец «{key}» не найден. left_on задаётся с префиксом (base.column или alias.column), "
                                     f"right_on — без префикса. Доступные столбцы: {available}")
        for left_key, right_key in zip(left_on, right_on):
            left_type, right_type = _key_type(result[left_key]), _key_type(right[right_key])
            if "empty" not in (left_type, right_type) and left_type != right_type:
                raise DataSelectionError(f"Типы ключей «{left_key}» и «{right_key}» различаются; автоматического преобразования нет")
            if left_type.startswith("mixed") or right_type.startswith("mixed"):
                raise ValueError("Столбцы ключей содержат значения разных типов")

        how = step.get("how", "left")
        relationship = step.get("relationship", "many_to_one")
        result = result.assign(_join_left_order=range(len(result)))
        right = right.assign(_join_right_order=range(len(right)))
        # SQL semantics: a missing component never matches another missing key.
        left_missing = result[left_on].isna().any(axis=1)
        right_missing = right[right_on].isna().any(axis=1)
        left_valid, right_valid = result.loc[~left_missing], right.loc[~right_missing]
        left_counts = left_valid.groupby(left_on, sort=False, observed=True).size().rename("left_count").reset_index()
        right_counts = right_valid.groupby(right_on, sort=False, observed=True).size().rename("right_count").reset_index()
        counts = left_counts.merge(right_counts, left_on=left_on, right_on=right_on, how="outer", sort=False)
        left_n = counts["left_count"].fillna(0).astype("int64")
        right_n = counts["right_count"].fillna(0).astype("int64")
        matched_pairs = sum(int(left) * int(right_count) for left, right_count in zip(left_n, right_n))
        matched_left = int(left_n[right_n > 0].sum())
        matched_right = int(right_n[left_n > 0].sum())
        unmatched_left = len(result) - matched_left
        unmatched_right = len(right) - matched_right
        output_count = matched_pairs
        if how in ("left", "outer"):
            output_count += unmatched_left
        if how in ("right", "outer"):
            output_count += unmatched_right
        if output_count > MAX_JOIN_ROWS:
            raise ValueError(f"Соединение создаст {output_count} строк (максимум {MAX_JOIN_ROWS}). Уточните ключи или сократите таблицы")

        try:
            joined = left_valid.merge(right_valid, left_on=left_on, right_on=right_on, how=how, sort=False, validate=relationship)
        except pd.errors.MergeError as exc:
            raise DataSelectionError(f"Нарушена связь {relationship}: {exc}. Уточните ключи; тип связи не меняется автоматически") from exc
        parts = [joined]
        if how in ("left", "outer") and left_missing.any():
            parts.append(result.loc[left_missing].reindex(columns=joined.columns))
        if how in ("right", "outer") and right_missing.any():
            parts.append(right.loc[right_missing].reindex(columns=joined.columns))
        steps.append({
            "source_id": step["source_id"], "alias": step["alias"],
            "how": how, "relationship": relationship,
            "left_on": left_on, "right_on": step["right_on"],
            "left_rows": len(result), "right_rows": len(right),
            "matched_pairs": matched_pairs,
            "unmatched_left_rows": unmatched_left, "unmatched_right_rows": unmatched_right,
            "missing_left_keys": int(left_missing.sum()), "missing_right_keys": int(right_missing.sum()),
            "output_rows": output_count,
        })
        if ((left_n > 1) & (right_n > 1)).any():
            warnings.append(f"Соединение {step['alias']}: ключи повторяются с обеих сторон; проверьте размножение строк перед суммированием")
        result = pd.concat(parts, ignore_index=True) if len(parts) > 1 else joined
        order = ["_join_right_order", "_join_left_order"] if how == "right" else ["_join_left_order", "_join_right_order"]
        result = result.sort_values(order, kind="stable").drop(columns=order).reset_index(drop=True)
        columns.extend(right_columns)

    rows = []
    for record in result.head(limit).to_dict(orient="records"):
        rows.append({name: None if pd.isna(cell) else _json_value(cell) for name, cell in record.items()})
    return {
        "source_id": source_id, "columns": columns, "steps": steps, "warnings": warnings,
        "total_rows": len(result), "returned_count": len(rows),
        "limit": limit, "truncated": len(result) > limit, "rows": rows,
    }
