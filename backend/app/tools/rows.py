import pandas as pd
from app.tools.column_values import _prepare_value


def get_rows(df: pd.DataFrame, column: str, value, limit: int = 10) -> dict:
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
    if not pd.api.types.is_scalar(value):
        raise ValueError("Укажите одно значение для поиска")

    if pd.isna(value):
        matches = df[column].isna()
        search_value = None
    else:
        matches = df[column].eq(value).fillna(False)
        search_value = _prepare_value(value)

    matched_count = int(matches.sum())
    selected_rows = df.loc[matches].head(limit)
    
    rows = []
    for record in selected_rows.to_dict(orient="records"):
        row = {}
        for name, cell in record.items():
            row[name] = None if pd.isna(cell) else _prepare_value(cell)
        rows.append(row)

    return {
        "column": column,
        "value": search_value,
        "total_rows": len(df),
        "matched_count": matched_count,
        "returned_count": len(rows),
        "limit": limit,
        "truncated": matched_count > limit,
        "rows": rows,
    }
