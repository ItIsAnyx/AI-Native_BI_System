"""Observational what-if regression; estimates associations, never causal effects."""
import numpy as np
import pandas as pd
from app.tools.preprocessing import _columns, _validate


def estimate_scenario(df, target_column, feature_columns, changes, baseline=None):
    _validate(df, 10)
    features = _columns(df, feature_columns)
    _columns(df, [target_column])
    if target_column in features or len(features) > 10:
        raise ValueError("Выберите до 10 признаков без целевого показателя")
    keys = set(df.attrs.get("key_columns", [])) | {df.attrs.get("technical_id_column")}
    if keys.intersection([target_column, *features]):
        raise ValueError("Идентификаторы нельзя использовать как показатели регрессии")
    if any(not pd.api.types.is_numeric_dtype(df[c]) or pd.api.types.is_bool_dtype(df[c]) for c in [target_column, *features]):
        raise ValueError("Цель и признаки должны быть числовыми")
    if not isinstance(changes, dict) or not changes or not set(changes).issubset(features):
        raise ValueError("Изменения должны задавать новые значения известных признаков")
    if baseline is not None and (not isinstance(baseline, dict) or set(baseline) != set(features)):
        raise ValueError("Базовый сценарий должен содержать значения всех признаков")
    for values in (changes, baseline or {}):
        if any(isinstance(v, bool) or not isinstance(v, (int, float)) or not np.isfinite(v) for v in values.values()):
            raise ValueError("Значения сценария должны быть конечными числами")
    data = df[[*features, target_column]].dropna().astype(float)
    data = data.loc[np.isfinite(data).all(axis=1)]
    if len(data) < max(8, 2 * (len(features) + 1) + 1):
        raise ValueError("Недостаточно наблюдений для регрессии; нужен больший датасет")
    x, y = data[features].to_numpy(), data[target_column].to_numpy()
    mean, scale = x.mean(axis=0), x.std(axis=0)
    if (scale == 0).any():
        raise ValueError("Признаки должны изменяться в наблюдениях")
    design = np.column_stack([np.ones(len(data)), (x - mean) / scale])
    if np.linalg.matrix_rank(design) < design.shape[1]:
        raise ValueError("Признаки линейно зависимы; выберите независимые признаки")
    coefficients = np.linalg.lstsq(design, y, rcond=None)[0]
    base = baseline or dict(zip(features, mean.tolist()))
    changed = {**base, **changes}
    def predict(values):
        row = np.array([values[c] for c in features])
        return float(np.r_[1, (row - mean) / scale] @ coefficients)
    before, after = predict(base), predict(changed)
    residual = y - design @ coefficients
    total_variance = float(((y - y.mean()) ** 2).sum())
    extrapolated = [c for i, c in enumerate(features) if changed[c] < x[:, i].min() or changed[c] > x[:, i].max()]
    return {"method": "observational_multiple_linear_regression", "target_column": target_column,
            "features": features, "used_rows": len(data), "excluded_rows": len(df) - len(data),
            "baseline_values": base, "baseline_is_sample_mean": baseline is None, "scenario_values": changed,
            "baseline_prediction": before, "scenario_prediction": after, "difference": after - before,
            "coefficients": dict(zip(features, (coefficients[1:] / scale).tolist())),
            "training_r_squared": 1 - float((residual ** 2).sum()) / total_variance if total_variance else None,
            "residual_standard_error": float(np.sqrt((residual ** 2).sum() / (len(data) - design.shape[1]))),
            "extrapolated_features": extrapolated,
            "note": "Условная оценка по наблюдаемым связям, не причинный эффект и не гарантированный прогноз. Другие признаки зафиксированы; без заданной базы используются средние выборки. R² рассчитан на обучающей выборке и не доказывает качество на новых данных. Вне наблюдаемого диапазона — экстраполяция."}


SCENARIO_TOOL = {"type": "function", "function": {"name": "estimate_scenario",
    "description": "Оценить сценарий по наблюдаемой многомерной линейной регрессии, например связь цены с показателем при фиксированных остальных признаках. changes задаёт НОВЫЕ значения признаков в исходных единицах, не проценты. Не выдумывай новые значения; уточни их у пользователя. Можно предварительно отфильтровать сегмент. Это не причинный эффект.",
    "parameters": {"type": "object", "additionalProperties": False, "properties": {
        "target_column": {"type": "string"}, "feature_columns": {"type": "array", "minItems": 1, "maxItems": 10, "items": {"type": "string"}},
        "changes": {"type": "object", "minProperties": 1, "additionalProperties": {"type": "number"}},
        "baseline": {"type": "object", "additionalProperties": {"type": "number"}, "description": "Значения всех признаков для базы. Если не задано — средние выборки, что явно сообщается."}},
        "required": ["target_column", "feature_columns", "changes"]}}}
