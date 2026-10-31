"""Exploratory time analysis with explicit cadence, assumptions and no implicit gap fill."""
import numpy as np
import pandas as pd

from app.tools.time_series import _dates
from app.tools.preprocessing import _columns

FREQUENCIES = {"day": "D", "week": "W-SUN", "month": "M", "quarter": "Q", "year": "Y"}


def _series(df, date_column, columns, frequency, aggregation, date_format):
    if frequency not in FREQUENCIES or aggregation not in {"sum", "mean"}:
        raise ValueError("Укажите частоту day/week/month/quarter/year и агрегацию sum/mean")
    _columns(df, columns)
    if any(c in df.attrs.get("key_columns", []) or c == df.attrs.get("technical_id_column") for c in columns):
        raise ValueError("Выберите показатели, а не идентификаторы")
    if any(not pd.api.types.is_numeric_dtype(df[c]) or pd.api.types.is_bool_dtype(df[c]) for c in columns):
        raise ValueError("Показатели должны быть числовыми")
    dates, details = _dates(df, date_column, date_format, "UTC")
    valid = dates.notna() & df[columns].notna().all(axis=1)
    for c in columns:
        valid &= np.isfinite(df[c]).fillna(False)
    data = df.loc[valid, columns].copy()
    data.index = dates.loc[valid].dt.tz_localize(None).dt.to_period(FREQUENCIES[frequency])
    data = data.groupby(level=0).agg(aggregation).sort_index()
    if len(data) < 4:
        raise ValueError("Нужно минимум четыре наблюдаемых периода")
    if len(pd.period_range(data.index.min(), data.index.max(), freq=FREQUENCIES[frequency])) != len(data):
        raise ValueError("Во временном ряду есть пропущенные периоды. Уточните срез или частоту; пропуски не заменяются нулями.")
    if not np.isfinite(data.to_numpy(dtype=float)).all():
        raise ValueError("После агрегации получены бесконечные значения")
    return data, {**details, "frequency": frequency, "aggregation": aggregation,
                  "included_rows": int(valid.sum()), "excluded_rows": int((~valid).sum()), "periods": len(data)}


def analyze_seasonality(df, date_column, value_column, cycle_length=12, frequency="month", aggregation="sum", date_format="ISO8601"):
    if type(cycle_length) is not int or not 2 <= cycle_length <= 366:
        raise ValueError("Длина цикла должна быть от 2 до 366 периодов")
    data, details = _series(df, date_column, [value_column], frequency, aggregation, date_format)
    values = data[value_column].to_numpy(dtype=float)
    if len(values) < 3 * cycle_length:
        raise ValueError("Для оценки повторяемости нужны минимум три полных цикла")
    x = np.arange(len(values))
    residual = values - np.polyval(np.polyfit(x, values, 1), x)
    a, b = residual[:-cycle_length], residual[cycle_length:]
    corr = float(np.corrcoef(a, b)[0, 1]) if np.std(a) > 1e-10 and np.std(b) > 1e-10 else None
    return {**details, "cycle_length": cycle_length, "detrended_cycle_correlation": corr,
            "cycle_profile": [{"position": i + 1, "mean": float(values[i::cycle_length].mean())}
                              for i in range(cycle_length)],
            "note": "Разведочная оценка повторяемости после удаления линейного тренда. Не является статистическим доказательством сезонности; позиция 1 соответствует первому периоду ряда."}


def analyze_lags(df, date_column, first_column, second_column, max_lag=5, frequency="day", aggregation="sum", date_format="ISO8601"):
    if first_column == second_column:
        raise ValueError("Выберите два разных показателя")
    if type(max_lag) is not int or not 0 <= max_lag <= 90:
        raise ValueError("Максимальный лаг должен быть от 0 до 90 периодов")
    data, details = _series(df, date_column, [first_column, second_column], frequency, aggregation, date_format)
    if len(data) - max_lag < 4:
        raise ValueError("Для каждого лага нужно минимум четыре пары наблюдений")
    results = []
    for lag in range(max_lag + 1):
        a = data[first_column].to_numpy(dtype=float)[:len(data) - lag]
        b = data[second_column].to_numpy(dtype=float)[lag:]
        corr = float(np.corrcoef(a, b)[0, 1]) if np.std(a) > 0 and np.std(b) > 0 else None
        results.append({"lag": lag, "pairs": len(a), "correlation": corr})
    return {**details, "lags": results,
            "note": "Лаг k сравнивает первый показатель в t со вторым в t+k. Корреляция не доказывает причинность; тренды и перебор лагов могут давать ложные связи."}


def forecast_series(df, date_column, value_column, horizon=4, frequency="quarter", aggregation="sum", scenario_percent=0, date_format="ISO8601"):
    if type(horizon) is not int or not 1 <= horizon <= 24:
        raise ValueError("Горизонт должен быть от 1 до 24 периодов")
    if isinstance(scenario_percent, bool) or not isinstance(scenario_percent, (int, float)) or not np.isfinite(scenario_percent) or not -100 <= scenario_percent <= 1000:
        raise ValueError("Сценарное изменение должно быть числом от −100 до 1000 процентов")
    data, details = _series(df, date_column, [value_column], frequency, aggregation, date_format)
    y = data[value_column].to_numpy(dtype=float)
    x = np.arange(len(y), dtype=float)
    slope, intercept = np.polyfit(x, y, 1)
    residual = y - (intercept + slope * x)
    variance = float(np.dot(residual, residual) / (len(y) - 2))
    future = np.arange(len(y), len(y) + horizon, dtype=float)
    baseline = intercept + slope * future
    error = 1.96 * np.sqrt(variance * (1 + 1 / len(y) + (future - x.mean()) ** 2 / ((x - x.mean()) ** 2).sum()))
    periods = pd.period_range(data.index[-1] + 1, periods=horizon, freq=data.index.freq)
    return {**details, "method": "ordinary_least_squares_linear_trend", "scenario_percent": scenario_percent,
            "forecast": [{"period": str(p), "baseline": float(v), "lower_approx_95": float(v - e),
                          "upper_approx_95": float(v + e), "scenario": float(v * (1 + scenario_percent / 100))}
                         for p, v, e in zip(periods, baseline, error)],
            "note": "Линейная экстраполяция, без учёта сезонности и внешних факторов. Интервал приблизительный, предполагает независимые ошибки с постоянной дисперсией. Сценарий — заданное пользователем процентное изменение прогноза, а не оценка влияния цены или причинная модель."}


def schema(name, description, extra, required):
    return {"type": "function", "function": {"name": name, "description": description,
        "parameters": {"type": "object", "additionalProperties": False,
                       "properties": {"date_column": {"type": "string"},
                                      "frequency": {"type": "string", "enum": list(FREQUENCIES)},
                                      "aggregation": {"type": "string", "enum": ["sum", "mean"]},
                                      "date_format": {"type": "string", "default": "ISO8601"}, **extra},
                       "required": ["date_column", *required]}}}


ADVANCED_FUNCTIONS = {f.__name__: f for f in (analyze_seasonality, analyze_lags, forecast_series)}
ADVANCED_TOOLS = [
    schema("analyze_seasonality", "Разведочная оценка повторяемости временного ряда: корреляция с циклом после удаления тренда, профиль цикла. Требует 3 полных цикла, не заполняет отсутствующие периоды.",
           {"value_column": {"type": "string"}, "cycle_length": {"type": "integer", "minimum": 2, "maximum": 366, "default": 12}}, ["value_column"]),
    schema("analyze_lags", "Корреляции первого показателя в t со вторым в t+k для k=0..max_lag. Не является доказательством причинности. Частоту и показатели выбирай по запросу.",
           {"first_column": {"type": "string"}, "second_column": {"type": "string"}, "max_lag": {"type": "integer", "minimum": 0, "maximum": 90, "default": 5}}, ["first_column", "second_column"]),
    schema("forecast_series", "Линейная экстраполяция и приблизительный 95% интервал. Сценарный процент задаёт пользователь; не угадывай влияние цены. Не заполняет пропуски периодов, минимум 4 периода.",
           {"value_column": {"type": "string"}, "horizon": {"type": "integer", "minimum": 1, "maximum": 24, "default": 4},
            "scenario_percent": {"type": "number", "minimum": -100, "maximum": 1000, "default": 0}}, ["value_column"]),
]
