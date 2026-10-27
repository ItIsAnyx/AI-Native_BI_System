import re

import pandas as pd
from app.tools.column_values import _json_value
from app.tools.errors import DataSelectionError


def _period_boundary(value: str) -> pd.Timestamp:
    if not isinstance(value, str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}(?:[T ].+)?", value):
        raise ValueError("Границы периода должны быть датами YYYY-MM-DD или датами со временем ISO 8601")
    try:
        timestamp = pd.Timestamp(value)
        return timestamp.tz_localize("UTC") if timestamp.tzinfo is None else timestamp.tz_convert("UTC")
    except (ValueError, TypeError, OverflowError) as exc:
        raise ValueError(f"Некорректная граница периода: {value!r}") from exc


def get_rows_by_period(
    df: pd.DataFrame, column: str, start_date: str, end_date: str,
    limit: int = 10, date_format: str = "ISO8601",
) -> dict:
    if not isinstance(df, pd.DataFrame):
        raise TypeError("Нужно передать таблицу pandas.DataFrame")
    if not isinstance(column, str) or not column:
        raise ValueError("Укажите название столбца")
    if column not in df.columns:
        raise ValueError(f"Столбец «{column}» не найден")
    if not df.columns.is_unique:
        raise ValueError("Названия столбцов в таблице не должны повторяться")
    if type(limit) is not int or not 1 <= limit <= 1000:
        raise ValueError("Количество результатов должно быть целым числом от 1 до 1000")
    if not isinstance(date_format, str) or not date_format or date_format == "mixed":
        raise ValueError("Укажите формат дат: ISO8601 или явный шаблон, например %d.%m.%Y")

    start = _period_boundary(start_date)
    end = _period_boundary(end_date)
    end_is_day = len(end_date) == 10
    # A date without a time includes the entire last day, at any precision.
    if end_is_day:
        try:
            end += pd.Timedelta(days=1)
        except (ValueError, OverflowError) as exc:
            raise ValueError("Конец периода выходит за допустимый диапазон дат") from exc
    if start > end or (end_is_day and start == end):
        raise DataSelectionError("Начало периода не должно быть позже конца; уточните границы, не меняя их автоматически")

    values = df[column]
    missing = values.isna() | values.astype("string").str.strip().eq("").fillna(False)
    # CSV dates are strings. Numbers must not become Unix timestamps implicitly.
    dates = pd.to_datetime(values.astype("string"), format=date_format, errors="coerce", utc=True)
    matches = dates.ge(start) & (dates.lt(end) if end_is_day else dates.le(end))
    matched_count = int(matches.sum())
    selected_rows = df.loc[matches].head(limit)

    rows = []
    for record in selected_rows.to_dict(orient="records"):
        row = {}
        for name, cell in record.items():
            row[name] = None if pd.isna(cell) else _json_value(cell)
        rows.append(row)

    return {
        "column": column,
        "start_date": start_date,
        "end_date": end_date,
        "date_format": date_format,
        "timezone": "UTC",
        "total_rows": len(df),
        "missing_count": int(missing.sum()),
        "invalid_count": int((dates.isna() & ~missing).sum()),
        "matched_count": matched_count,
        "returned_count": len(rows),
        "limit": limit,
        "truncated": matched_count > limit,
        "rows": rows,
    }
