from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

import pandas as pd

from app.tools.grouping import group_dataset
from app.tools.preprocessing import _columns, _validate


TIME_FREQUENCIES = ("day", "week", "month", "quarter", "year", "month_of_year", "quarter_of_year", "weekday")


def _dates(df, column, date_format, timezone):
    _validate(df, 10)
    _columns(df, [column])
    if not isinstance(date_format, str) or not date_format or date_format == "mixed":
        raise ValueError("Укажите формат дат: ISO8601 или явный шаблон, например %d.%m.%Y")
    if not isinstance(timezone, str):
        raise ValueError("Укажите часовой пояс, например UTC или Europe/Moscow")
    try:
        ZoneInfo(timezone)
    except (ZoneInfoNotFoundError, ValueError) as exc:
        raise ValueError("Неизвестный часовой пояс") from exc
    values = df[column]
    missing = values.isna() | values.astype("string").str.strip().eq("").fillna(False)
    dates = pd.to_datetime(values.astype("string"), format=date_format, errors="coerce", utc=True).dt.tz_convert(timezone)
    return dates, {
        "date_column": column, "date_format": date_format, "timezone": timezone,
        "missing_count": int(missing.sum()), "invalid_count": int((dates.isna() & ~missing).sum()),
    }


def get_date_range(df: pd.DataFrame, column: str, date_format: str = "ISO8601", timezone: str = "UTC") -> dict:
    dates, details = _dates(df, column, date_format, timezone)
    valid = dates.dropna()
    return {
        **details, "total_rows": len(df), "valid_count": len(valid),
        "start_date": valid.min().isoformat() if len(valid) else None,
        "end_date": valid.max().isoformat() if len(valid) else None,
        "distinct_days": int(valid.dt.date.nunique()),
        "source_warnings": list(df.attrs.get("warnings", [])),
    }


def group_by_time(
    df: pd.DataFrame, date_column: str, frequency: str, aggregations: list[dict],
    group_by: list[str] | None = None, period_alias: str = "period", date_format: str = "ISO8601",
    timezone: str = "UTC", dropna: bool = False, limit: int = 10,
) -> dict:
    _validate(df, limit)
    if frequency not in TIME_FREQUENCIES:
        raise ValueError("Неизвестная частота календарной группировки")
    if not isinstance(period_alias, str) or not period_alias.strip() or len(period_alias) > 128 or period_alias in df.columns:
        raise ValueError("period_alias должен быть новым непустым именем до 128 символов")
    keys = [] if group_by is None else _columns(df, group_by)
    if date_column in keys:
        raise ValueError("В group_by укажите только дополнительные признаки, без date_column: дата уже сгруппирована по frequency")
    dates, details = _dates(df, date_column, date_format, timezone)
    valid = dates.notna()
    local = dates.loc[valid].dt.tz_localize(None)
    if frequency == "month_of_year":
        periods = local.dt.month
    elif frequency == "quarter_of_year":
        periods = local.dt.quarter
    elif frequency == "weekday":
        periods = local.dt.dayofweek + 1
    else:
        code = {"day": "D", "week": "W-SUN", "month": "M", "quarter": "Q", "year": "Y"}[frequency]
        periods = local.dt.to_period(code).dt.start_time.dt.strftime("%Y-%m-%d")
    data = df.loc[valid].copy()
    data[period_alias] = periods
    result = group_dataset(data, [period_alias, *keys], aggregations, dropna=dropna, sort_by=period_alias, limit=limit)
    result.update({
        **details, "operation": "group_by_time", "frequency": frequency, "period_alias": period_alias,
        "input_rows": len(df), "excluded_rows": len(df) - result["included_rows"],
        "source_warnings": list(df.attrs.get("warnings", [])),
    })
    return result
