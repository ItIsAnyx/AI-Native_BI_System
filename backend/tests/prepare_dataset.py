from pathlib import Path

import pandas as pd

source = Path.home() / "Downloads" / "01_Продажи.csv"

destination = (
    Path(__file__).resolve().parent / "datasets" / "sales_sample.csv"
)
destination.parent.mkdir(exist_ok=True)

df = pd.read_csv(
    source,
    encoding="utf-8-sig",
    sep=";",
    decimal=",",
    nrows=1000,
)

df.to_csv(destination, index=False, encoding="utf-8")

print(f"Файл сохранён: {destination}")
print(f"Количество строк: {len(df)}")
print(f"Размер таблицы: {df.shape}")
print(f"Столбцы: {list(df.columns)}")

numeric_columns = df.select_dtypes(include="number").columns

for column in numeric_columns:
    print(f"\nСтолбец: {column}")
    print(f"Среднее: {df[column].mean():.4f}")
    print(f"Минимум: {df[column].min()}")
    print(f"Максимум: {df[column].max()}")
    print(f"Пропусков: {df[column].isna().sum()}")

print(df.head(3).to_string(index=False))