import base64
import io
import threading
import numpy as np
import pandas as pd
from matplotlib import rc_context
from matplotlib.backends.backend_agg import FigureCanvasAgg
from matplotlib.figure import Figure

CHART_TYPES = ("line", "scatter", "bar", "barh", "area", "pie", "histogram")
AGGREGATIONS = ("none", "sum", "mean", "count")
_RENDER_LOCK = threading.Lock()


def build_chart(df: pd.DataFrame, x_column: str, y_column: str,
                chart_type: str, aggregation: str = "none",
                title: str = "", limit: int = 1000) -> dict:
    if not isinstance(df, pd.DataFrame):
        raise TypeError("Нужно передать таблицу pandas.DataFrame")
    if not df.columns.is_unique:
        raise ValueError("Названия столбцов не должны повторяться")
    for column in (x_column, y_column):
        if not isinstance(column, str) or not column or column not in df.columns:
            raise ValueError(f"Столбец {column!r} не найден")
    if chart_type == "histogram" and (x_column != y_column or aggregation != "none"):
        raise ValueError("Для histogram укажите один показатель в X и Y, aggregation=none")
    if x_column == y_column and chart_type != "histogram":
        raise ValueError("Выберите два разных столбца")
    if chart_type not in CHART_TYPES:
        raise ValueError(f"chart_type: выберите один из {CHART_TYPES}")
    if aggregation not in AGGREGATIONS:
        raise ValueError(f"aggregation: выберите один из {AGGREGATIONS}")
    if type(limit) is not int or not 1 <= limit <= 1000:
        raise ValueError("limit должен быть целым числом от 1 до 1000")
    if not isinstance(title, str) or len(title) > 200:
        raise ValueError("title должен быть строкой длиной до 200 символов")

    data = df[list(dict.fromkeys([x_column, y_column]))].dropna().copy()
    for column in (x_column, y_column):
        if pd.api.types.is_numeric_dtype(data[column]):
            data = data.loc[np.isfinite(data[column])]
    valid_rows = len(data)
    if data.empty:
        raise ValueError("Нет пар значений без пропусков и бесконечностей")
    category_column = y_column if chart_type == "barh" else x_column
    value_column = x_column if chart_type == "barh" else y_column
    if aggregation != "count" and (
        not pd.api.types.is_numeric_dtype(data[value_column])
        or pd.api.types.is_bool_dtype(data[value_column])
    ):
        raise ValueError("Столбец величин должен быть числовым (X для barh, Y для остальных); для подсчёта выберите count")
    if aggregation != "none":
        data = data.groupby(category_column, sort=False, observed=True)[value_column].agg(aggregation).reset_index()
    if chart_type in ("scatter", "area") and (
        not pd.api.types.is_numeric_dtype(data[x_column])
        or pd.api.types.is_bool_dtype(data[x_column])
    ):
        raise ValueError("Для scatter и area столбец X должен быть числовым")
    if chart_type in ("line", "area"):
        data = data.sort_values(x_column, kind="stable")
    if not np.isfinite(data[value_column].to_numpy(dtype=float)).all():
        raise ValueError("После агрегации получены бесконечные значения")
    if chart_type == "pie" and ((data[y_column] < 0).any() or data[y_column].sum() <= 0):
        raise ValueError("Для pie нужны неотрицательные значения с положительной суммой")
    available_points = len(data)
    data = data.head(limit)
    if chart_type == "pie" and data[y_column].sum() <= 0:
        raise ValueError("В выбранных точках сумма для pie должна быть положительной")

    with _RENDER_LOCK, rc_context({"text.parse_math": False}):
        figure = Figure(figsize=(10, 6), layout="constrained")
        FigureCanvasAgg(figure)
        ax = figure.subplots()
        x, y = data[x_column].tolist(), data[y_column].tolist()
        if chart_type in ("bar", "barh"):
            categories = data[category_column].tolist()
            values = data[value_column].tolist()
            positions = list(range(len(categories)))
            if chart_type == "bar":
                ax.bar(positions, values)
                ax.set_xticks(positions, [str(value) for value in categories], rotation=45, ha="right")
            else:
                ax.barh(positions, values)
                ax.set_yticks(positions, [str(value) for value in categories])
        elif chart_type == "histogram":
            ax.hist(x, bins="auto")
        elif chart_type == "pie":
            ax.pie(y, labels=[str(value) for value in x], autopct="%1.1f%%")
        elif chart_type == "area":
            ax.fill_between(x, y)
        elif chart_type == "scatter":
            ax.scatter(x, y)
        else:
            ax.plot(x, y)
        if chart_type != "pie":
            ax.set_xlabel(x_column)
            ax.set_ylabel("Количество наблюдений" if chart_type == "histogram" else y_column)
        ax.set_title(title or f"{value_column} / {category_column}", parse_math=False)
        output = io.BytesIO()
        figure.savefig(output, format="png", dpi=120)

    return {
        "chart_type": chart_type, "title": title, "x_column": x_column, "y_column": y_column,
        "aggregation": aggregation, "total_rows": len(df), "valid_rows": valid_rows,
        "excluded_rows": len(df) - valid_rows, "available_points": available_points,
        "plotted_points": len(data), "truncated": available_points > len(data),
        "mime_type": "image/png",
        "image_base64": base64.b64encode(output.getvalue()).decode("ascii"),
    }
