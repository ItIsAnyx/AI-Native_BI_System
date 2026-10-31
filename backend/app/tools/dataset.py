import csv
from collections import Counter
import json
import math
import re
from io import StringIO
import pandas as pd
from app.services.cancellation import checkpoint
from fastapi import HTTPException
from app.config import settings
from app.services import chat_storage
from app.data.processed_dataset import metadata_path, read_processed_dataset

from app.tools.column_values import get_column_values as get_column_values
from app.tools.rows import get_rows as get_rows
from app.tools.relationships import analyze_relationship as analyze_relationship


def dataset_column_names(header: list[str], width: int, warnings: list[str]) -> list[str]:
    reserved = {name.strip() for name in header if name.strip()}
    columns = []
    for index in range(width):
        original = header[index].strip() if index < len(header) else ""
        name = original or (f"column_{index + 1}" if index < len(header) else f"_extra_column_{index - len(header) + 1}")
        base = name
        suffix = 2
        while name in columns or (name != original and name in reserved):
            name = f"{base}__{suffix}"
            suffix += 1
        columns.append(name)
        if index < len(header) and name != original:
            problem = "пустой" if not original else "повторяется"
            warnings.append(f"Заголовок столбца {index + 1} {original!r} {problem}; используется имя {name!r}.")
    return columns


def read_dataset(file) -> pd.DataFrame:
    warnings = []
    try:
        text = file.read()
        if isinstance(text, bytes):
            text = text.decode("utf-8-sig")
        else:
            text = text.lstrip("\ufeff")
        # A truncated sample and commas in unit labels can fool Sniffer into
        # splitting a semicolon file at decimal commas. Compare complete records.
        candidates = []
        for candidate in (",", ";", "\t"):
            parsed = []
            try:
                for row in csv.reader(StringIO(text[:65536]), delimiter=candidate, strict=True):
                    if row:
                        parsed.append(row)
                    if len(parsed) >= 32:
                        break
            except csv.Error:
                pass
            widths = Counter(map(len, parsed[1:] or parsed))
            if widths:
                width, matches = widths.most_common(1)[0]
                ratio = matches / sum(widths.values())
                if width > 1:
                    candidates.append(((len(parsed) > 1, len(parsed[0]) == width, ratio >= .8, width if ratio >= .8 else ratio, ratio), candidate))
        delimiter = max(candidates, key=lambda item: item[0])[1] if candidates else ","
        csv.field_size_limit(settings.MAX_FILE_SIZE_MB * 1024 * 1024)
        reader = csv.reader(StringIO(text, newline=""), delimiter=delimiter, strict=True)
        header = next(row for row in reader if row)
        rows = []
        mismatched_rows = 0
        examples = []
        for row in reader:
            if not row:
                continue
            if len(row) != len(header):
                mismatched_rows += 1
                if len(examples) < 5:
                    examples.append(f"строка {reader.line_num}: {len(row)} полей")
            rows.append(row)
            if len(rows) % 10000 == 0:
                checkpoint()
            if len(rows) > settings.MAX_FILE_ROWS:
                raise HTTPException(status_code=400, detail=f"Too many rows. Max: {settings.MAX_FILE_ROWS}")
    except HTTPException:
        raise
    except StopIteration as exc:
        raise HTTPException(status_code=400, detail="CSV is empty") from exc
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Cannot read CSV: {exc}") from exc

    width = max([len(header)] + [len(row) for row in rows])
    columns = dataset_column_names(header, width, warnings)
    if mismatched_rows:
        warnings.append(
            f"В {mismatched_rows} строках число полей отличается от заголовка ({len(header)}): "
            + "; ".join(examples)
            + ". Недостающие поля отмечены как пропуски; дополнительные поля сохранены в отдельных столбцах."
        )
    df = pd.DataFrame([row + [None] * (width - len(row)) for row in rows], columns=columns, dtype="string")
    key_columns = []
    for column in columns:
        values = df[column].str.strip().replace("", pd.NA)
        words = re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", column).casefold()
        named_key = bool({"id", "uuid", "guid", "код", "артикул", "идентификатор"} & set(re.findall(r"[^\W\d_]+", words)))
        leading_zeros = bool(values.str.fullmatch(r"[+-]?0\d+").any())
        if named_key or leading_zeros:
            key_columns.append(column)
            if leading_zeros or not values.dropna().str.fullmatch(r"[+-]?\d+").all():
                warnings.append(
                    f"Столбец {column!r} распознан как возможный ключ и сохранён строками: "
                    "есть ведущие нули, буквы или другие нечисловые обозначения. Проверьте назначение столбца."
                )
        elif values.notna().any():
            try:
                values = pd.to_numeric(values, errors="raise")
            except (ValueError, TypeError):
                complete = values.dropna()
                if delimiter in (";", "\t") and complete.str.fullmatch(r"[+-]?(?:\d+(?:,\d+)?|,\d+)(?:[eE][+-]?\d+)?").all():
                    values = pd.to_numeric(values.str.replace(",", ".", regex=False), errors="raise")
                    warnings.append(f"Столбец {column!r}: распознана десятичная запятая.")
        df[column] = values
    technical_id = "_row_id"
    while technical_id in df.columns:
        technical_id = "_" + technical_id
    df.insert(0, technical_id, range(1, len(df) + 1))
    df.attrs["warnings"] = warnings
    df.attrs["key_columns"] = key_columns
    df.attrs["technical_id_column"] = technical_id
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
        "warnings": list(df.attrs.get("warnings", [])),
        "key_columns": list(df.attrs.get("key_columns", [])),
        "technical_id_column": df.attrs.get("technical_id_column"),
    }

def get_dataset_columns(df: pd.DataFrame) -> dict:
    """Expose schema and small value samples without calculating full statistics."""
    descriptions = df.attrs.get("column_descriptions", {})
    samples = json.loads(df.head(3).to_json(orient="records"))
    technical_id = df.attrs.get("technical_id_column")
    return {"columns": [
        {"name": column, "dtype": str(df[column].dtype),
         "description": descriptions.get(column),
         "is_technical_id": column == technical_id,
         "is_possible_key": column in df.attrs.get("key_columns", []),
         "sample_values": [row[column] for row in samples]}
        for column in df.columns
    ], "description_note": "Null descriptions mean no verified business definition is available. "
       "Any interpretation based on names or samples must be identified as an inference."}


def read_dataset_and_gain_statistics(df: pd.DataFrame) -> dict:
    return info_to_str(df)


def list_sources(sources: list[dict]) -> list[dict]:
    return [
        {key: source[key] for key in ("id", "name", "description", "type")}
        for source in sources
    ]


def load_source(sources: list[dict], source_id: str | None):
    source = next((source for source in sources if source["id"] == source_id), None)
    if source is None:
        raise ValueError("Select an available data source using source_id")
    path = chat_storage.existing_file(source["file_path"])
    if source["type"] == "postgresql":
        from app.data.postgres_source import read_table
        return read_table(json.loads(path.read_text(encoding="utf-8")))
    if metadata_path(path).is_file():
        return read_processed_dataset(path)
    with path.open("rb") as file:
        return read_dataset(file)
