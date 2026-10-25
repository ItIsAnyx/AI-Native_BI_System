import base64
import io
import math

import numpy as np
import pandas as pd
from matplotlib import image, rc_context
from matplotlib.backends.backend_agg import FigureCanvasAgg
from matplotlib.figure import Figure

from app.tools.charts import _RENDER_LOCK, build_chart
from app.tools.preprocessing import _validate


def build_dashboard(df: pd.DataFrame, panels: list[dict], title: str = "Dashboard") -> dict:
    _validate(df, 10)
    if not isinstance(title, str) or not title.strip() or len(title) > 200:
        raise ValueError("Укажите название дашборда длиной от 1 до 200 символов")
    if not isinstance(panels, list) or not 2 <= len(panels) <= 6:
        raise ValueError("Дашборд должен содержать от 2 до 6 графиков")
    allowed = {"x_column", "y_column", "chart_type", "aggregation", "title", "limit"}
    for panel in panels:
        if not isinstance(panel, dict) or set(panel) - allowed or not {"x_column", "y_column", "chart_type"} <= set(panel):
            raise ValueError("Каждый график требует x_column, y_column и chart_type; неизвестные параметры запрещены")
    # All panels must succeed before an artifact is returned or saved.
    charts = [build_chart(df, **panel) for panel in panels]
    usable = pd.Series(False, index=df.index)
    for panel in panels:
        columns = [panel["x_column"], panel["y_column"]]
        complete = df[columns].notna().all(axis=1)
        for column in columns:
            if pd.api.types.is_numeric_dtype(df[column]):
                complete &= np.isfinite(df[column]).fillna(False)
        usable |= complete
    with _RENDER_LOCK, rc_context({"text.parse_math": False}):
        figure = Figure(figsize=(16, 6 * math.ceil(len(charts) / 2)), layout="constrained")
        FigureCanvasAgg(figure)
        axes = list(figure.subplots(math.ceil(len(charts) / 2), 2, squeeze=False).flat)
        for axis, chart in zip(axes, charts):
            axis.imshow(image.imread(io.BytesIO(base64.b64decode(chart["image_base64"])), format="png"))
            axis.set_axis_off()
        for axis in axes[len(charts):]:
            axis.set_axis_off()
        figure.suptitle(title, parse_math=False)
        output = io.BytesIO()
        figure.savefig(output, format="png", dpi=120)
    return {
        "chart_type": "dashboard", "title": title, "x_column": "", "y_column": "",
        "aggregation": "none", "total_rows": len(df),
        # A row is usable when at least one panel can display its pair of values.
        "valid_rows": int(usable.sum()), "excluded_rows": int((~usable).sum()),
        "available_points": sum(chart["available_points"] for chart in charts),
        "plotted_points": sum(chart["plotted_points"] for chart in charts),
        "truncated": any(chart["truncated"] for chart in charts),
        "panels": [{**{key: value for key, value in chart.items() if key != "image_base64"},
                    "title": panel.get("title", "")} for panel, chart in zip(panels, charts)],
        "mime_type": "image/png", "image_base64": base64.b64encode(output.getvalue()).decode("ascii"),
    }
