import numpy as np
import pandas as pd

from app.tools.preprocessing import _columns, _numeric, _rows, _validate


GROUP_AGGREGATIONS = ("sum", "mean", "median", "min", "max", "count", "nunique", "size")


def _integer_sum(grouped, unsigned):
    totals = []
    lower, upper = (0, 2 ** 64 - 1) if unsigned else (-(2 ** 63), 2 ** 63 - 1)
    for _, values in grouped:
        complete = values.dropna()
        total = sum(int(value) for value in complete) if len(complete) else pd.NA
        if total is not pd.NA and not lower <= total <= upper:
            raise ValueError("Сумма выходит за диапазон целых чисел; результат без потери точности получить нельзя")
        totals.append(total)
    return pd.Series(totals, dtype="UInt64" if unsigned else "Int64")


def group_dataset(
    df: pd.DataFrame, group_by: list[str], aggregations: list[dict],
    dropna: bool = False, sort_by: str | None = None, ascending: bool = True, limit: int = 10,
) -> dict:
    _validate(df, limit)
    group_by = _columns(df, group_by)
    if not isinstance(aggregations, list) or not 1 <= len(aggregations) <= 50:
        raise ValueError("Укажите от 1 до 50 агрегатов")
    if type(dropna) is not bool or type(ascending) is not bool:
        raise ValueError("dropna и ascending должны быть логическими значениями")
    for name in group_by:
        kind = pd.api.types.infer_dtype(df[name].dropna(), skipna=True)
        if kind.startswith("mixed") and kind != "mixed-integer-float":
            raise ValueError(f"Столбец группировки «{name}» содержит значения разных типов")

    aliases = set(group_by)
    for aggregation in aggregations:
        if not isinstance(aggregation, dict) or set(aggregation) - {"column", "function", "alias"}:
            raise ValueError("Некорректные параметры агрегата")
        function, alias = aggregation.get("function"), aggregation.get("alias")
        if function not in GROUP_AGGREGATIONS:
            raise ValueError("Неизвестная функция агрегации")
        if not isinstance(alias, str) or not alias.strip() or len(alias) > 128 or alias in aliases:
            raise ValueError("alias должен быть уникальным непустым именем до 128 символов и не совпадать с ключами группировки")
        aliases.add(alias)
        if function == "size":
            if "column" in aggregation:
                raise ValueError("Для size столбец не задаётся: функция считает все строки группы")
            continue
        column = aggregation.get("column")
        if column is None:
            raise ValueError(f"Для {function} нужен column. Если требуется количество всех строк группы, "
                             "используйте function=size без column; сохраните запрошенный alias")
        _columns(df, [column])
        if function in ("sum", "mean", "median"):
            _numeric(df, column, protect_keys=True)
        if function in ("sum", "mean", "median", "min", "max") and pd.api.types.is_numeric_dtype(df[column]):
            if not np.isfinite(df[column].dropna()).all():
                raise ValueError(f"В «{column}» есть бесконечности; сначала отфильтруйте их")
    if sort_by is not None and (not isinstance(sort_by, str) or sort_by not in aliases):
        raise ValueError("sort_by должен быть названием столбца результата")

    grouped = df.groupby(group_by, dropna=dropna, observed=True, sort=False)
    sizes = grouped.size()
    result = sizes.index.to_frame(index=False)
    for aggregation in aggregations:
        function = aggregation["function"]
        if function == "size":
            metric = sizes
        else:
            column = aggregation["column"]
            values = grouped[column]
            if function == "sum":
                if pd.api.types.is_integer_dtype(df[column]):
                    metric = _integer_sum(values, pd.api.types.is_unsigned_integer_dtype(df[column]))
                else:
                    metric = values.sum(min_count=1)
            else:
                metric = getattr(values, function)()
        if function in ("sum", "mean", "median") and not np.isfinite(metric.dropna()).all():
            raise ValueError("Агрегация привела к бесконечному результату; проверьте диапазон чисел")
        result[aggregation["alias"]] = pd.Series(metric.array, index=result.index)
    if sort_by is not None:
        result = result.sort_values(sort_by, ascending=ascending, kind="stable", na_position="last").reset_index(drop=True)
    result.attrs = {"warnings": [], "key_columns": list(group_by), "technical_id_column": None}
    included_rows = int(sizes.sum())
    return {
        "operation": "group_dataset", "input_rows": len(df), "included_rows": included_rows,
        "excluded_rows": len(df) - included_rows, "total_rows": len(result), "group_count": len(result),
        "group_by": list(group_by), "aggregations": aggregations, "dropna": dropna,
        "sort_by": sort_by, "ascending": ascending, "columns": list(result.columns),
        "returned_count": min(limit, len(result)), "limit": limit, "truncated": len(result) > limit,
        "rows": _rows(result.head(limit)), "source_warnings": list(df.attrs.get("warnings", [])),
        "_dataframe": result,
    }
