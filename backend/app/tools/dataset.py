import json
import math
import pandas as pd
from fastapi import HTTPException
from app.config import settings

from app.tools.column_values import get_column_values as get_column_values
from app.tools.rows import get_rows as get_rows
from app.tools.relationships import analyze_relationship as analyze_relationship

def read_dataset(file) -> pd.DataFrame:
    try:
        df = pd.read_csv(file, encoding="utf-8-sig", nrows=settings.MAX_FILE_ROWS + 1)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Cannot read CSV: {exc}") from exc

    if len(df) > settings.MAX_FILE_ROWS:
        raise HTTPException(status_code=400, detail=f"Too many rows. Max: {settings.MAX_FILE_ROWS}")

    df.columns = df.columns.str.strip()
    if df.columns.duplicated().any():
        raise HTTPException(status_code=400, detail="Duplicate column names after stripping spaces")
    for column in df.select_dtypes(include=["object", "string"]).columns:
        df[column] = df[column].str.strip()
    return df

def info_to_str(df: pd.DataFrame) -> dict:
    columns_info = {}
    for column in df.columns:
        values = df[column]
        columns_info[column] = {
            "dtype": str(values.dtype),
            "non_null": int(values.notna().sum()),
            "null": int(values.isna().sum()),
            "unique": int(values.nunique()),
        }
        if pd.api.types.is_numeric_dtype(values):
            statistics = {
                "mean": values.mean(),
                "min": values.min(),
                "max": values.max(),
                "median": values.median(),
            }
            for name, value in statistics.items():
                if pd.isna(value) or not math.isfinite(value):
                    columns_info[column][name] = None
                else:
                    columns_info[column][name] = round(float(value), 4)

    return {
        "total_rows": len(df),
        "columns": columns_info,
        "example_strings": json.loads(df.head(5).to_json(orient="records")),
    }
