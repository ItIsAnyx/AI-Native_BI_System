from app.tools.column_values import get_column_values
from app.tools.rows import get_rows
from app.tools.relationships import analyze_relationship
from app.tools.charts import build_chart, CHART_TYPES, AGGREGATIONS
from app.tools.dataset import list_sources, read_dataset_and_gain_statistics

TOOL_FUNCTIONS = {
    "list_sources": list_sources,
    "build_chart": build_chart,
    "read_dataset_and_gain_statistics": read_dataset_and_gain_statistics,
    "get_column_values": get_column_values,
    "get_rows": get_rows,
    "analyze_relationship": analyze_relationship,
}

tools = [
    {
        "type": "function",
        "function": {
            "name": "list_sources",
            "description": "Получить ID, названия и описания CSV-источников текущего чата. Внутренние пути не возвращаются.",
            "parameters": {"type": "object", "properties": {}, "additionalProperties": False},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "build_chart",
            "description": "Построить график по двум столбцам сохранённого CSV-источника чата. Выбери тип по запросу: line — динамика, scatter — связь чисел, bar/barh — сравнение, area — площадь, pie — доли. Для повторяющихся категорий явно выбери sum, mean или count, если этого требует запрос. PNG возвращается пользователю отдельно; не придумывай ссылку на файл. Пропуски и бесконечности исключаются попарно. При превышении limit берутся первые точки после агрегации и сортировки; для line/area X сортируется по возрастанию.",
            "parameters": {
                "type": "object",
                "properties": {
                    "x_column": {"type": "string", "minLength": 1, "description": "Столбец горизонтальной оси X. Для barh — числовые величины (длины полос), для остальных — категории или аргумент."},
                    "y_column": {"type": "string", "minLength": 1, "description": "Столбец вертикальной оси Y. Для barh — категории, для остальных — числовые величины."},
                    "chart_type": {"type": "string", "enum": list(CHART_TYPES)},
                    "aggregation": {"type": "string", "enum": list(AGGREGATIONS), "default": "none", "description": "Используй none, если пользователь не просил сумму, среднее или количество. Не агрегируй только ради построения графика."},
                    "title": {"type": "string", "maxLength": 200},
                    "limit": {"type": "integer", "minimum": 1, "maximum": 1000, "default": 1000},
                },
                "required": ["x_column", "y_column", "chart_type"],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "read_dataset_and_gain_statistics",
            "description": "Получить структуру и статистику CSV-источника чата: число строк, названия и типы столбцов, пропуски, уникальные значения, среднее, минимум, максимум, медиану числовых столбцов и пять примеров строк. Используй, когда нужны эти сведения или названия столбцов для другого инструмента. Датасет подставляет приложение; source_id можно не указывать для активного источника.",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": [],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_column_values",
            "description": "Получить значения столбца и частоту каждого по всей таблице. Пропуски считаются отдельно.",
            "parameters": {
                "type": "object",
                "properties": {
                    "column": {"type": "string", "minLength": 1, "description": "Точное название столбца."},
                    "limit": {"type": "integer", "minimum": 1, "maximum": 1000, "default": 10,
                              "description": "Сколько самых частых значений показать."},
                },
                "required": ["column"],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_rows",
            "description": "Найти строки по точному совпадению значения столбца. Учитываются регистр и пробелы. Число не заменяется текстом.",
            "parameters": {
                "type": "object",
                "properties": {
                    "column": {"type": "string", "minLength": 1, "description": "Точное название столбца."},
                    "value": {"type": ["string", "number", "boolean", "null"],
                              "description": "Искомое значение; null означает поиск пропусков."},
                    "limit": {"type": "integer", "minimum": 1, "maximum": 1000, "default": 10,
                              "description": "Сколько найденных строк показать."},
                },
                "required": ["column", "value"],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "analyze_relationship",
            "description": "Исследовать два столбца одной таблицы: частые пары значений и однозначность соответствия в обе стороны. Для числовых показателей также считать корреляцию Пирсона. Не использовать корреляцию для идентификаторов и не трактовать её как причинность.",
            "parameters": {
                "type": "object",
                "properties": {
                    "first_column": {"type": "string", "minLength": 1, "description": "Точное название первого столбца."},
                    "second_column": {"type": "string", "minLength": 1, "description": "Точное название другого столбца."},
                    "limit": {"type": "integer", "minimum": 1, "maximum": 1000, "default": 10,
                              "description": "Сколько самых частых пар показать. Анализ использует всю таблицу."},
                },
                "required": ["first_column", "second_column"],
                "additionalProperties": False,
            },
        },
    },
]

for tool in tools:
    if tool["function"]["name"] != "list_sources":
        tool["function"]["parameters"]["properties"]["source_id"] = {
            "type": "string",
            "description": "ID CSV-источника из list_sources. Если не указан, используется активный источник чата.",
        }
