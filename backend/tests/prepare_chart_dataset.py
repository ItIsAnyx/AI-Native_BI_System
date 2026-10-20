"""Prepare the local CSV and append chart cases to the shared scenarios.py."""
from pathlib import Path
from pprint import pformat


CSV = "month,revenue,region\n1,10,A\n2,20,B\n3,30,A\n4,40,B\n5,50,A\n6,60,B\n7,70,A\n8,80,B\n"
CHART_SCENARIOS = [
    {
        "name": "chart_line",
        "message": "Покажи динамику revenue по month линейным графиком.",
        "expected": "Один line PNG: X=month, Y=revenue, aggregation=none, 8 точек (1,10)...(8,80). Текст соответствует графику.",
        "file": "datasets/chart_data.csv",
    },
    {
        "name": "chart_scatter",
        "message": "Построй диаграмму рассеяния: X — month, Y — revenue.",
        "expected": "Один scatter PNG: X=month, Y=revenue, aggregation=none, 8 точек (1,10)...(8,80). Текст соответствует графику.",
        "file": "datasets/chart_data.csv",
    },
    {
        "name": "chart_bar",
        "message": "Сравни суммарную revenue по region на столбчатой диаграмме.",
        "expected": "Один bar PNG: X=region, Y=revenue, aggregation=sum, 2 столбца A=160, B=200; учтены все 8 строк. Текст соответствует значениям.",
        "file": "datasets/chart_data.csv",
    },
    {
        "name": "chart_barh",
        "message": "Построй горизонтальную столбчатую диаграмму revenue по month.",
        "expected": "Один barh PNG: X=revenue, Y=month, aggregation=none, 8 полос шириной 10...80 для месяцев 1...8. Текст соответствует графику.",
        "file": "datasets/chart_data.csv",
    },
    {
        "name": "chart_area",
        "message": "Построй график с заливкой площади (area): X — month, Y — revenue.",
        "expected": "Один area PNG: X=month, Y=revenue, aggregation=none (не sum), 8 точек (1,10)...(8,80). Текст соответствует графику.",
        "file": "datasets/chart_data.csv",
    },
    {
        "name": "chart_pie",
        "message": "Покажи доли суммарной revenue по region на круговой диаграмме.",
        "expected": "Один pie PNG: X=region, Y=revenue, aggregation=sum. A=160 (44.4%), B=200 (55.6%), всего 360; учтены все 8 строк. Числа в тексте должны совпадать.",
        "file": "datasets/chart_data.csv",
    },
    {
        "name": "chart_no_attachment",
        "message": "Построй график по полному датасету из предыдущего запроса.",
        "expected": "Передан реальный context предыдущего ответа, но CSV не прикреплён. charts=[]; модель просит повторно приложить файл, не выдумывает данные и не утверждает, что построила график.",
        "use_previous_context": True,
    },
]


def prepare():
    root = Path(__file__).resolve().parent
    dataset = root / "datasets" / "chart_data.csv"
    dataset.parent.mkdir(exist_ok=True)
    if dataset.exists() and dataset.read_text(encoding="utf-8-sig") != CSV:
        raise SystemExit(f"Файл уже существует с другими данными: {dataset}")
    dataset.write_text(CSV, encoding="utf-8")
    scenarios = root / "scenarios.py"
    source = scenarios.read_text(encoding="utf-8-sig") if scenarios.exists() else ""
    if "CHART_SCENARIOS" not in source:
        with scenarios.open("a", encoding="utf-8") as target:
            target.write("\n\nCHART_SCENARIOS = " + pformat(CHART_SCENARIOS, sort_dicts=False, width=100) + "\n")
        print(f"Добавлены 7 сценариев: {scenarios}")
    else:
        print("CHART_SCENARIOS уже есть; существующие сценарии сохранены.")
    print(f"Датасет: {dataset} (8 строк, A=160, B=200)")


if __name__ == "__main__":
    prepare()
