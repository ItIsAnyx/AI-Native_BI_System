import math
import pandas as pd
from app.tools.column_values import _json_value


def _get_correlation(data, first_column, second_column):
    result = {"method": "pearson", "value": None, "used_rows": 0, "note": ""}
    for column in [first_column, second_column]:
        if not pd.api.types.is_numeric_dtype(data[column]) or pd.api.types.is_bool_dtype(data[column]):
            result["note"] = "Корреляция считается только для двух числовых столбцов"
            return result

    numbers = data.replace([float("inf"), float("-inf")], float("nan")).dropna()
    result["used_rows"] = len(numbers)
    if len(numbers) < 3:
        result["note"] = "Для расчёта нужно хотя бы три строки с конечными числами."
    elif numbers[first_column].nunique() < 2 or numbers[second_column].nunique() < 2:
        result["note"] = "Корреляция не определена: один из столбцов постоянный."
    else:
        coefficient = float(numbers.corr().loc[first_column, second_column])
        if math.isfinite(coefficient):
            result["value"] = round(coefficient, 6)
            result["note"] = "Пирсон оценивает линейную связь. Корреляция не доказывает причинность."
        else:
            result["note"] = "Не удалось получить конечный коэффициент корреляции."
    return result


def analyze_relationship(df: pd.DataFrame, first_column: str, second_column: str, limit: int = 10) -> dict:
    if not isinstance(df, pd.DataFrame):
        raise TypeError("Нужно передать таблицу pandas.DataFrame")
    for column in [first_column, second_column]:
        if not isinstance(column, str) or not column:
            raise ValueError("Укажите названия двух столбцов")
        if column not in df.columns:
            raise ValueError(f"Столбец «{column}» не найден")
    if first_column == second_column:
        raise ValueError("Выберите два разных столбца")
    if not df.columns.is_unique:
        raise ValueError("Названия столбцов в таблице не должны повторяться")
    if type(limit) is not int or not 1 <= limit <= 1000:
        raise ValueError("Количество результатов должно быть целым числом от 1 до 1000")

    data = df[[first_column, second_column]].dropna()
    counts = data.value_counts(sort=False)
    counts = counts[counts > 0].sort_values(ascending=False, kind="stable")

    pairs = []
    for (first_value, second_value), count in counts.head(limit).items():
        pairs.append({
            "first_value": _json_value(first_value),
            "second_value": _json_value(second_value),
            "count": int(count),
        })

    first_to_second = None
    second_to_first = None
    if not data.empty:
        second_per_first = data.groupby(first_column, observed=True, sort=False)[second_column].nunique()
        first_per_second = data.groupby(second_column, observed=True, sort=False)[first_column].nunique()
        first_to_second = bool((second_per_first == 1).all())
        second_to_first = bool((first_per_second == 1).all())

    return {
        "first_column": first_column,
        "second_column": second_column,
        "total_rows": len(df),
        "complete_rows": len(data),
        "missing_rows": len(df) - len(data),
        "unique_pairs": len(counts),
        "returned_count": len(pairs),
        "limit": limit,
        "truncated": len(counts) > limit,
        "first_to_second_unique": first_to_second,
        "second_to_first_unique": second_to_first,
        "pairs": pairs,
        "correlation": _get_correlation(data, first_column, second_column),
        "note": "Связи описывают только наблюдаемые строки. Числовые идентификаторы не следует трактовать как показатели.",
    }
