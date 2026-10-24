import math
from numbers import Real

import numpy as np
import pandas as pd
from app.tools.column_values import _json_value
from app.tools.errors import DataSelectionError


MISSING_STRATEGIES = ("drop_rows", "constant", "mean", "median", "mode")
FILTER_OPERATORS = ("eq", "ne", "gt", "ge", "lt", "le", "in", "not_in", "between", "is_null", "not_null", "is_finite", "not_finite")


def _validate(df, limit):
    if not isinstance(df, pd.DataFrame):
        raise TypeError("Нужно передать таблицу pandas.DataFrame")
    if not df.columns.is_unique or any(not isinstance(name, str) for name in df.columns):
        raise ValueError("Названия столбцов должны быть уникальными строками")
    if type(limit) is not int or not 1 <= limit <= 1000:
        raise ValueError("Количество результатов должно быть целым числом от 1 до 1000")


def _columns(df, columns, default=False):
    if columns is None and default:
        columns = [name for name in df.columns if name != df.attrs.get("technical_id_column")]
    if not isinstance(columns, list) or not columns or any(not isinstance(name, str) or not name for name in columns):
        raise ValueError("Укажите непустой список столбцов")
    if len(set(columns)) != len(columns):
        raise ValueError("Столбцы не должны повторяться")
    for name in columns:
        if name not in df.columns:
            raise DataSelectionError(f"Столбец «{name}» не найден")
    return columns


def _missing(values):
    empty_strings = values.map(lambda value: isinstance(value, str) and not value.strip()).fillna(False).astype(bool)
    return values.isna() | empty_strings


def _rows(df):
    return [{name: None if pd.isna(value) else _json_value(value) for name, value in row.items()}
            for row in df.to_dict(orient="records")]


def _result(df, result, operation, limit, **details):
    result = result.copy(deep=True)
    result.attrs = {
        **df.attrs,
        "key_columns": [name for name in df.attrs.get("key_columns", []) if name in result.columns],
        "technical_id_column": df.attrs.get("technical_id_column") if df.attrs.get("technical_id_column") in result.columns else None,
    }
    return {
        "operation": operation, "input_rows": len(df), "total_rows": len(result),
        "removed_rows": len(df) - len(result), "columns": list(result.columns),
        "returned_count": min(limit, len(result)), "limit": limit, "truncated": len(result) > limit,
        "rows": _rows(result.head(limit)), **details, "_dataframe": result,
    }


def _numeric(df, column, protect_keys=False):
    values = df[column]
    if not pd.api.types.is_numeric_dtype(values) or pd.api.types.is_bool_dtype(values):
        raise DataSelectionError(f"Столбец «{column}» должен быть числовым; автоматического преобразования нет")
    if protect_keys and column in [df.attrs.get("technical_id_column"), *df.attrs.get("key_columns", [])]:
        raise DataSelectionError(f"Столбец «{column}» является идентификатором, а не числовым показателем")
    return values


def _check_value(values, value):
    if not isinstance(value, (str, Real, bool)) or pd.isna(value):
        raise ValueError("Значение должно быть строкой, конечным числом или логическим значением")
    if isinstance(value, Real) and not math.isfinite(value):
        raise ValueError("Числовое значение должно быть конечным")
    if values.dropna().empty:
        return
    kind = pd.api.types.infer_dtype(values.dropna(), skipna=True)
    if kind == "empty":
        return
    if pd.api.types.is_bool_dtype(values) or kind == "boolean":
        compatible = isinstance(value, bool)
    elif pd.api.types.is_numeric_dtype(values) or kind in ("integer", "floating", "mixed-integer-float"):
        compatible = isinstance(value, Real) and not isinstance(value, bool)
    elif isinstance(values.dtype, pd.StringDtype) or kind in ("string", "unicode", "empty"):
        compatible = isinstance(value, str)
    else:
        compatible = False
    if not compatible:
        raise ValueError("Тип значения не совпадает с типом столбца; автоматического преобразования нет")


def clean_missing_values(df: pd.DataFrame, columns: list[str] | None = None,
                         strategy: str = "drop_rows", value=None, limit: int = 10) -> dict:
    _validate(df, limit)
    columns = _columns(df, columns, default=True)
    if strategy not in MISSING_STRATEGIES:
        raise ValueError("Укажите стратегию drop_rows, constant, mean, median или mode")
    if strategy != "constant" and value is not None:
        raise ValueError("value задаётся только для стратегии constant")
    result = df.copy(deep=True)
    masks = {name: _missing(result[name]) for name in columns}
    before = {name: int(mask.sum()) for name, mask in masks.items()}
    affected = pd.DataFrame(masks).any(axis=1)
    filled = {}
    if strategy == "drop_rows":
        result = result.loc[~affected]
    else:
        for name in columns:
            values = result[name].mask(masks[name], pd.NA)
            if strategy == "constant":
                _check_value(values, value)
                if isinstance(value, str) and not value.strip():
                    raise ValueError("Для заполнения пропусков укажите непустое значение")
                replacement = value
            elif strategy in ("mean", "median"):
                _numeric(df, name, protect_keys=True)
                if not np.isfinite(values.dropna()).all():
                    raise ValueError(f"В «{name}» есть бесконечные значения; сначала отфильтруйте их")
                replacement = values.mean() if strategy == "mean" else values.median()
            else:
                modes = values.mode(dropna=True)
                replacement = modes.iloc[0] if len(modes) else None
            if before[name] == 0:
                continue
            if replacement is None or pd.isna(replacement):
                raise ValueError(f"В «{name}» нет данных для заполнения пропусков")
            if isinstance(replacement, Real) and not math.isfinite(replacement):
                raise ValueError(f"Не удалось получить конечное значение для «{name}»")
            try:
                if values.isna().all() and strategy == "constant":
                    result[name] = pd.Series(replacement, index=values.index)
                else:
                    result[name] = values.fillna(replacement)
            except (TypeError, ValueError) as exc:
                if pd.api.types.is_integer_dtype(values) and isinstance(replacement, Real) and not isinstance(replacement, bool):
                    if any(int(float(number)) != number for number in values.dropna()):
                        raise ValueError("Заполнение дробным числом приведёт к потере точности больших целых значений") from exc
                    result[name] = values.astype("Float64").fillna(replacement)
                else:
                    raise ValueError(f"Значение заполнения несовместимо со столбцом «{name}»") from exc
            filled[name] = _json_value(replacement)
    return _result(df, result, "clean_missing_values", limit, strategy=strategy,
                   missing_before=before, missing_after={name: int(_missing(result[name]).sum()) for name in columns},
                   affected_rows=int(affected.sum()), fill_values=filled)


def drop_columns(df: pd.DataFrame, columns: list[str], limit: int = 10) -> dict:
    _validate(df, limit)
    columns = _columns(df, columns)
    if len(columns) == len(df.columns):
        raise ValueError("В таблице должен остаться хотя бы один столбец")
    return _result(df, df.drop(columns=columns), "drop_columns", limit, removed_columns=columns)


def drop_duplicates(df: pd.DataFrame, subset: list[str] | None = None, keep: str = "first", limit: int = 10) -> dict:
    _validate(df, limit)
    subset = _columns(df, subset, default=True)
    if keep not in ("first", "last", "none"):
        raise ValueError("keep должен быть first, last или none")
    result = df.drop_duplicates(subset=subset, keep=False if keep == "none" else keep)
    return _result(df, result, "drop_duplicates", limit, subset=subset, keep=keep)


def find_duplicates(df: pd.DataFrame, subset: list[str] | None = None, limit: int = 10) -> dict:
    _validate(df, limit)
    subset = _columns(df, subset, default=True)
    duplicates = df.duplicated(subset=subset, keep=False)
    extra = df.duplicated(subset=subset, keep="first")
    duplicate_rows_count = int(duplicates.sum())
    duplicate_count = int(extra.sum())
    examples = df.loc[duplicates].head(limit)
    return {
        "operation": "find_duplicates", "total_rows": len(df), "subset": subset,
        "duplicate_count": duplicate_count, "duplicate_rows_count": duplicate_rows_count,
        "duplicate_group_count": duplicate_rows_count - duplicate_count,
        "returned_count": len(examples), "limit": limit,
        "truncated": duplicate_rows_count > len(examples), "rows": _rows(examples),
        "source_warnings": list(df.attrs.get("warnings", [])),
    }


def find_anomalies(df: pd.DataFrame, columns: list[str], method: str = "iqr", threshold: float | None = None, limit: int = 10) -> dict:
    _validate(df, limit)
    columns = _columns(df, columns)
    if method not in ("iqr", "zscore"):
        raise ValueError("method должен быть iqr или zscore")
    if threshold is None:
        threshold = 1.5 if method == "iqr" else 3.0
    if isinstance(threshold, bool) or not isinstance(threshold, Real) or not math.isfinite(threshold) or threshold <= 0:
        raise ValueError("threshold должен быть положительным конечным числом")
    flags = {}
    statistics = {}
    warnings = ["Статистическая аномалия не обязательно является ошибкой. Удаление выполняется отдельным фильтром по явному условию."]
    for name in columns:
        values = _numeric(df, name, protect_keys=True)
        finite_mask = values.notna() & np.isfinite(values).fillna(False)
        finite = values.loc[finite_mask]
        infinite = values.notna() & ~finite_mask
        lower = upper = None
        if len(finite) < (4 if method == "iqr" else 3):
            warnings.append(f"В «{name}» недостаточно конечных значений для метода {method}")
        elif method == "iqr":
            q1, q3 = finite.quantile([0.25, 0.75])
            lower, upper = float(q1 - threshold * (q3 - q1)), float(q3 + threshold * (q3 - q1))
        else:
            mean, std = float(finite.mean()), float(finite.std(ddof=0))
            lower, upper = mean - threshold * std, mean + threshold * std
        if lower is not None and (not math.isfinite(lower) or not math.isfinite(upper)):
            raise ValueError(f"Числа в «{name}» слишком велики для вычисления конечных границ")
        flag = infinite.copy()
        if lower is not None:
            flag |= finite_mask & (values.lt(lower) | values.gt(upper)).fillna(False)
        flags[name] = flag
        statistics[name] = {"lower_bound": lower, "upper_bound": upper, "finite_count": len(finite),
                            "missing_count": int(values.isna().sum()), "infinite_count": int(infinite.sum()),
                            "anomaly_count": int(flag.sum())}
    all_flags = pd.DataFrame(flags, index=df.index)
    selected = all_flags.any(axis=1)
    positions = np.flatnonzero(selected.to_numpy())[:limit]
    return {
        "method": method, "threshold": threshold, "total_rows": len(df),
        "anomaly_count": int(selected.sum()), "returned_count": len(positions), "limit": limit,
        "truncated": int(selected.sum()) > limit, "columns": statistics, "warnings": warnings,
        "rows": [{"values": _rows(df.iloc[[position]])[0],
                  "anomaly_columns": [name for name in columns if all_flags.iloc[position][name]]} for position in positions],
    }


def _condition(df, condition):
    if not isinstance(condition, dict) or set(condition) - {"column", "operator", "value"}:
        raise ValueError("Некорректное условие фильтрации")
    name, operator = condition.get("column"), condition.get("operator")
    _columns(df, [name])
    if operator not in FILTER_OPERATORS:
        raise ValueError("Неизвестный оператор фильтрации")
    values = df[name]
    missing = _missing(values)
    if operator in ("is_null", "not_null", "is_finite", "not_finite"):
        if "value" in condition:
            raise ValueError("Для проверки пропусков и конечности value не задаётся")
        if operator in ("is_null", "not_null"):
            return missing if operator == "is_null" else ~missing
        _numeric(df, name)
        finite = np.isfinite(values).fillna(False)
        return (~missing & finite) if operator == "is_finite" else (~missing & ~finite)
    value = condition.get("value")
    if operator in ("in", "not_in", "between"):
        if not isinstance(value, list) or not 1 <= len(value) <= 1000:
            raise ValueError("Для in, not_in и between value должен быть непустым списком до 1000 значений")
        for item in value:
            _check_value(values, item)
    else:
        _check_value(values, value)
    if operator in ("gt", "ge", "lt", "le", "between"):
        _numeric(df, name)
    if operator == "between":
        if len(value) != 2 or value[0] > value[1]:
            raise ValueError("Для between нужны нижняя и верхняя границы в этом порядке")
        mask = values.between(*value, inclusive="both")
    elif operator in ("in", "not_in"):
        mask = values.isin(value)
        if operator == "not_in":
            mask = ~mask
    else:
        mask = getattr(values, operator)(value)
    return mask.fillna(False) & ~missing


def filter_rows(df: pd.DataFrame, conditions: list[dict], combine: str = "all", action: str = "keep", limit: int = 10) -> dict:
    _validate(df, limit)
    if not isinstance(conditions, list) or not 1 <= len(conditions) <= 50:
        raise ValueError("Укажите от 1 до 50 условий")
    if combine not in ("all", "any") or action not in ("keep", "remove"):
        raise ValueError("combine должен быть all или any, action — keep или remove")
    masks = pd.DataFrame({index: _condition(df, condition) for index, condition in enumerate(conditions)}, index=df.index)
    matches = masks.all(axis=1) if combine == "all" else masks.any(axis=1)
    result = df.loc[matches if action == "keep" else ~matches]
    return _result(df, result, "filter_rows", limit, conditions=conditions, combine=combine,
                   action=action, matched_count=int(matches.sum()))


PREPROCESSING_FUNCTIONS = {
    "clean_missing_values": clean_missing_values,
    "drop_columns": drop_columns,
    "drop_duplicates": drop_duplicates,
    "find_duplicates": find_duplicates,
    "find_anomalies": find_anomalies,
    "filter_rows": filter_rows,
}
TRANSFORM_TOOLS = set(PREPROCESSING_FUNCTIONS) - {"find_anomalies", "find_duplicates"}
