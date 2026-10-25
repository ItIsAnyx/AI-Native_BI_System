from pathlib import Path
from pprint import pformat


CSV = "date,region,revenue\n2024-07-01,North,10\n2024-07-31,South,20\n2025-01-01,North,30\n2025-04-01,South,40\n2025-07-01,North,50\n2025-07-31,South,60\n2025-12-31,North,70\nbad,South,80\n,North,90\n2023-01-01,South,100\n2026-01-01T00:30:00+03:00,North,110\n"
TOOL_DATASETS = {
    "calendar_sales.csv": CSV,
    "calendar_timezone.csv": "date,revenue\n2026-01-01T00:30:00+03:00,10\n2026-01-01T00:00:00Z,20\n",
    "calendar_invalid.csv": "date,revenue\nbad,10\n,20\n",
    "calendar_explicit.csv": "date,revenue\n31.01.2026,10\n01.02.2026,20\n",
    "calendar_weeks.csv": "date,revenue\n2026-01-04,10\n2026-01-05,20\n2026-01-11,30\n",
    "calendar_dst.csv": "date,revenue\n2018-11-04T03:30:00Z,10\n2018-11-05T02:30:00Z,20\n",
}
TIME_SCENARIOS = [
    {"name": "date_range_dst", "message": "Определи диапазон date и число различных календарных дней в часовом поясе America/Sao_Paulo.",
     "expected": "2 дня. Начало 2018-11-04T01:30:00-02:00, конец 2018-11-05T00:30:00-02:00. Переход через несуществующую полночь не вызывает ошибки.", "file": "datasets/calendar_dst.csv"},
    {"name": "date_range_full", "message": "За какой период данные по date? Определи точные минимум и максимум по всему источнику, число различных дней, пропущенных и неверных дат.",
     "expected": "get_date_range: 11 строк, 9 дат, 8 дней; минимум 2023-01-01T00:00:00+00:00, максимум 2025-12-31T21:30:00+00:00, missing=1 invalid=1. Источник не изменён. Границы за пределами первых пяти строк.", "file": "datasets/calendar_sales.csv"},
    {"name": "date_range_empty", "message": "Определи диапазон дат столбца date по всей таблице.",
     "expected": "Диапазон null–null; valid_count=0 missing_count=1 invalid_count=1. Без выдуманных дат.", "file": "datasets/calendar_invalid.csv"},
    {"name": "date_range_format", "message": "Определи диапазон date. Формат дат явно %d.%m.%Y.",
     "expected": "2026-01-31–2026-02-01, 2 даты, пропусков и ошибок нет.", "file": "datasets/calendar_explicit.csv"},
    {"name": "date_range_missing", "message": "Определи диапазон дат missing_date. Не заменяй другим столбцом.",
     "expected": "Отсутствующий столбец отклонён или запрошено уточнение; диапазон date не выдан как результат missing_date.", "file": "datasets/calendar_sales.csv"},
    {"name": "time_quarter", "message": "Сгруппируй по date по календарным кварталам разных лет в UTC. sum revenue как total, size как records. Столбец начала квартала назови quarter. Покажи все группы.",
     "expected": "6 групп: 2023-01-01 total=100 records=1; 2024-07-01 30/2; 2025-01-01 30/1; 2025-04-01 40/1; 2025-07-01 110/2; 2025-10-01 180/2. Вход 11, учтено 9, исключено 2; missing=1 invalid=1. Новый активный CSV.", "file": "datasets/calendar_sales.csv"},
    {"name": "time_july", "message": "Посчитай суммарную revenue за каждый июль вместе по всем годам: сначала сгруппируй по номеру месяца date (month_of_year) с sum revenue как total и size как records, затем оставь только period=7.",
     "expected": "Календарная группировка и filter_rows. Единственная строка period=7 total=140 records=4. Исходник сохранён.", "file": "datasets/calendar_sales.csv"},
    {"name": "time_segments", "message": "Сгруппируй по date с frequency=month_of_year и дополнительно по region. sum revenue как total. Покажи все группы.",
     "expected": "6 групп: month1 North30 South100; month4 South40; month7 North60 South80; month12 North180. Учтено 9 строк. Ошибки дат сообщены.", "file": "datasets/calendar_sales.csv"},
    {"name": "time_week", "message": "Сгруппируй date по календарным неделям с понедельника. sum revenue как total. Начало недели назови week.",
     "expected": "week=2025-12-29 total=10; week=2026-01-05 total=50. Воскресенье завершает предыдущую неделю.", "file": "datasets/calendar_weeks.csv"},
    {"name": "time_timezone", "message": "Сгруппируй date по дням в часовом поясе Europe/Moscow. sum revenue как total.",
     "expected": "Одна группа period=2026-01-01 total=30. В UTC были бы два разных дня.", "file": "datasets/calendar_timezone.csv"},
    {"name": "time_preview", "message": "Сгруппируй date по кварталам: sum revenue как total, period_alias=quarter, limit=1. Только один пример, но сохрани полный результат.",
     "expected": "6 групп в новом CSV, пример 2023-01-01 total=100, truncated=true; не только один квартал в сохранённом источнике.", "file": "datasets/calendar_sales.csv", "save_source_as": "original"},
    {"name": "time_followup", "message": "В активной таблице оставь total >= 100. Покажи все строки.",
     "expected": "Без загрузки: 3 квартала 2023-01-01=100, 2025-07-01=110, 2025-10-01=180. Полный результат предыдущего шага доступен.", "use_previous_context": True},
    {"name": "time_original", "message": "Сколько строк в исходном источнике?",
     "expected": "Исходник содержит 11 строк, не изменён группировкой и фильтром.", "use_previous_context": True, "source_alias": "original"},
    {"name": "time_invalid_metric", "message": "Сгруппируй date по кварталам и суммируй region как total. Не заменяй сумму количеством.",
     "expected": "Суммирование текста отклонено/уточнение. Нового источника с подменой агрегата нет.", "file": "datasets/calendar_sales.csv"},
]
DASHBOARD_SCENARIOS = [
    {"name": "chart_regression", "message": "Построй обычный line-график: X=date, Y=revenue, без агрегации. Не создавай дашборд.",
     "expected": "Один сохранённый line PNG, X=date Y=revenue aggregation=none, 3 точки: 2026-01-04=10, 2026-01-05=20, 2026-01-11=30. Дашборд не создаётся, обычные графики продолжают работать.", "file": "datasets/calendar_weeks.csv", "check_saved_artifacts": True},
    {"name": "dashboard_basic", "message": "Создай сохранённый дашборд Sales из двух графиков: bar суммарной revenue по region и pie суммарной revenue по region. Используй build_dashboard.",
     "expected": "Один сохранённый dashboard PNG, title=Sales, 2 panels с aggregation=sum. North=360 South=300, всего 660. Все 11 строк, даже с неверными/пустыми датами. Артефакт доступен после повторного открытия чата.", "file": "datasets/calendar_sales.csv", "check_saved_artifacts": True},
    {"name": "dashboard_quarter", "message": "Создай квартальный дашборд: сначала сгруппируй date по кварталам в UTC, sum revenue как total и size как records, period_alias=quarter. Затем build_dashboard с двумя line-панелями: total по quarter и records по quarter. Без повторной агрегации.",
     "expected": "Новый CSV из 6 кварталов и один dashboard PNG с двумя line-панелями, aggregation=none, по 6 точек; кварталы хронологически. 2 неверных/пустых даты исключены при группировке. PNG и настройки доступны в истории.", "file": "datasets/calendar_sales.csv", "check_saved_artifacts": True},
    {"name": "dashboard_invalid", "message": "Создай дашборд с двумя bar-панелями: сумма revenue по region, затем сумма missing_metric по region. Не заменяй отсутствующий столбец.",
     "expected": "Ошибка или уточнение, ни один частичный dashboard не сохранён. charts=[].", "file": "datasets/calendar_sales.csv"},
]


def prepare():
    root = Path(__file__).resolve().parent
    path = root / "scenarios.py"
    source = path.read_text(encoding="utf-8-sig") if path.exists() else ""
    marker = "# BEGIN CALENDAR AND DASHBOARD SCENARIOS"
    if marker in source:
        raise SystemExit("Сценарии уже подготовлены; существующий файл не изменён.")
    if any(name in source for name in ("TIME_SCENARIOS", "DASHBOARD_SCENARIOS")):
        raise SystemExit("Существующие наборы TIME_SCENARIOS/DASHBOARD_SCENARIOS сохранены; добавьте новые случаи вручную.")
    content = "\n\n" + marker + "\n"
    content += "TOOL_DATASETS = {**globals().get('TOOL_DATASETS', {}), **" + pformat(TOOL_DATASETS, sort_dicts=False) + "}\n"
    content += "TIME_SCENARIOS = " + pformat(TIME_SCENARIOS, sort_dicts=False, width=100) + "\n"
    content += "DASHBOARD_SCENARIOS = " + pformat(DASHBOARD_SCENARIOS, sort_dicts=False, width=100) + "\n"
    with path.open("a", encoding="utf-8") as target:
        target.write(content)
    print(f"Добавлено {len(TIME_SCENARIOS) + len(DASHBOARD_SCENARIOS)} сценариев в {path}")


if __name__ == "__main__":
    prepare()
