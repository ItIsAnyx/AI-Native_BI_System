import math
from datetime import date, datetime, time
from numbers import Integral, Real

import pandas as pd


def _json_value(value):
    if isinstance(value, (datetime, date, time)):
        return value.isoformat()
    if isinstance(value, bool):
        return value
    if pd.api.types.is_bool(value):
        return bool(value)
    if isinstance(value, Integral):
        return int(value)
    if isinstance(value, Real):
        number = float(value)
        return number if math.isfinite(number) else str(number)
    return str(value)


def get_column_values(df: pd.DataFrame, column: str, limit: int = 10) -> dict:
    if not isinstance(df, pd.DataFrame):
        raise TypeError("df должен быть pandas.DataFrame")
    if not isinstance(column, str) or not column:
        raise ValueError("column должен быть непустым названием столбца")
    if isinstance(limit, bool) or not isinstance(limit, int) or not 1 <= limit <= 1000:
        raise ValueError("limit должен быть целым числом от 1 до 1000")
    if column not in df.columns:
        raise ValueError(f"Столбец {column!r} не найден")
    values = df[column]
    if not isinstance(values, pd.Series):
        raise ValueError(f"Название столбца {column!r} повторяется в таблице")

    counts = values.value_counts(dropna=True, sort=False)
    counts = counts[counts > 0].sort_values(ascending=False, kind="stable")
    top = counts.head(limit)
    return {
        "column": column,
        "total_rows": len(values),
        "missing_count": int(values.isna().sum()),
        "unique_count": len(counts),
        "returned_count": len(top),
        "limit": limit,
        "truncated": len(counts) > len(top),
        "values": [
            {"value": _json_value(value), "count": int(count)}
            for value, count in top.items()
        ],
    }
