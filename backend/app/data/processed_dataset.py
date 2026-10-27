import json
from pathlib import Path

import pandas as pd
from app.tools.column_values import _json_value


def metadata_path(path: Path) -> Path:
    return path.with_suffix(path.suffix + ".frame.json")


def write_processed_dataset(df: pd.DataFrame, path: Path) -> None:
    # The CSV is downloadable; the snapshot preserves types, literal NA strings,
    # large integer keys and the original technical IDs on subsequent requests.
    snapshot = {
        "version": 1,
        "columns": [{"name": name, "dtype": str(df[name].dtype),
                     "values": [None if pd.isna(value) else _json_value(value) for value in df[name]]}
                    for name in df.columns],
        "attrs": {key: df.attrs.get(key) for key in ("warnings", "key_columns", "technical_id_column")},
    }
    encoded = json.dumps(snapshot, ensure_ascii=False, allow_nan=False)
    created = []
    try:
        with path.open("x", encoding="utf-8-sig", newline="") as file:
            created.append(path)
            df.to_csv(file, index=False)
        companion = metadata_path(path)
        with companion.open("x", encoding="utf-8") as file:
            created.append(companion)
            file.write(encoded)
    except Exception:
        for item in created:
            item.unlink(missing_ok=True)
        raise


def read_processed_dataset(path: Path) -> pd.DataFrame:
    with metadata_path(path).open(encoding="utf-8") as file:
        snapshot = json.load(file)
    if snapshot.get("version") != 1:
        raise ValueError("Неизвестный формат обработанного датасета")
    columns = snapshot["columns"]
    result = pd.DataFrame({column["name"]: pd.Series(column["values"], dtype=column["dtype"]) for column in columns})
    result.attrs = {key: value for key, value in snapshot["attrs"].items() if value is not None}
    return result
