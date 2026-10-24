from app.tools.column_values import get_column_values
from app.tools.rows import get_rows
from app.tools.period import get_rows_by_period
from app.tools.joins import join_tables, JOIN_TYPES, JOIN_RELATIONSHIPS
from app.tools.relationships import analyze_relationship
from app.tools.charts import build_chart, CHART_TYPES, AGGREGATIONS
from app.tools.dataset import list_sources, read_dataset_and_gain_statistics
from app.tools.preprocessing import PREPROCESSING_FUNCTIONS, TRANSFORM_TOOLS as PREPROCESSING_TRANSFORMS
from app.tools.preprocessing_tools import PREPROCESSING_TOOLS
from app.tools.grouping import group_dataset, GROUP_AGGREGATIONS

TRANSFORM_TOOLS = PREPROCESSING_TRANSFORMS | {"group_dataset"}

TOOL_FUNCTIONS = {
    **PREPROCESSING_FUNCTIONS,
    "group_dataset": group_dataset,
    "list_sources": list_sources,
    "build_chart": build_chart,
    "read_dataset_and_gain_statistics": read_dataset_and_gain_statistics,
    "get_column_values": get_column_values,
    "get_rows": get_rows,
    "get_rows_by_period": get_rows_by_period,
    "join_tables": join_tables,
    "analyze_relationship": analyze_relationship,
}

tools = [
    {
        "type": "function",
        "function": {
            "name": "group_dataset",
            "description": "Сгруппировать CSV по одному или нескольким столбцам и посчитать именованные агрегаты. Не угадывай столбцы и функции при неоднозначном запросе. sum/mean/median применяются к числовым показателям, не к идентификаторам; min/max — также к тексту без разбора дат. count считает непустые значения столбца, nunique — различные непустые значения, size — все строки группы (без column). Пропуски в показателях пропускаются; sum для группы без значений возвращает null. Бесконечности перед sum/mean/median/min/max нужно отфильтровать. dropna=false сохраняет группы с пропусками ключей; true исключает строки с любым null в ключах. Порядок групп по первому появлению; sort_by сортирует результат, пропуски идут в конце. limit ограничивает только примеры, обработка выполняется по всей таблице. Создаёт новый CSV-источник и делает его активным; исходник сохраняется. Используй source_id результата для дальнейшего анализа. Сообщи число групп, excluded_rows и source_warnings.",
            "parameters": {
                "type": "object",
                "properties": {
                    "group_by": {"type": "array", "minItems": 1, "uniqueItems": True, "items": {"type": "string", "minLength": 1}, "description": "Точные названия столбцов группировки."},
                    "aggregations": {
                        "type": "array", "minItems": 1, "maxItems": 50,
                        "items": {
                            "type": "object",
                            "properties": {
                                "column": {"type": "string", "minLength": 1, "description": "Столбец показателя; для size не задаётся."},
                                "function": {"type": "string", "enum": list(GROUP_AGGREGATIONS)},
                                "alias": {"type": "string", "minLength": 1, "maxLength": 128, "description": "Уникальное название агрегата в результате, отличное от ключей группировки."},
                            },
                            "required": ["function", "alias"],
                            "additionalProperties": False,
                        },
                    },
                    "dropna": {"type": "boolean", "default": False},
                    "sort_by": {"type": "string", "minLength": 1, "description": "Столбец результата для сортировки."},
                    "ascending": {"type": "boolean", "default": True},
                    "limit": {"type": "integer", "minimum": 1, "maximum": 1000, "default": 10},
                },
                "required": ["group_by", "aggregations"],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "join_tables",
            "description": "Связать CSV текущего чата по заданным ключам. ID берутся из source_metadata или list_sources. Если пользователь уже задал ID и ключи, вызывай соединение напрямую; иначе уточни схему статистикой. left_on — ключи с префиксом base или ранее заданным alias (base.customer_id); right_on — исходное имя справа (id). Не угадывай ключи и не используй технический ID строки. Сохраняй заданные how и relationship: по умолчанию left, many_to_one. many_to_many — только по явному запросу. Null-ключи не совпадают; типы не преобразуются. Возвращает все столбцы с префиксами; total_rows — полный размер, rows — примеры. limit от 1 до 1000 ограничивает только примеры. Сообщи warnings и truncated. Новый CSV не создаётся.",
            "parameters": {
                "type": "object",
                "properties": {
                    "source_id": {"type": "string", "minLength": 1, "description": "ID основной CSV-таблицы из list_sources. Обязателен."},
                    "joins": {
                        "type": "array", "minItems": 1, "maxItems": 9,
                        "items": {
                            "type": "object",
                            "properties": {
                                "source_id": {"type": "string", "minLength": 1},
                                "alias": {"type": "string", "pattern": "^[A-Za-z][A-Za-z0-9_]{0,31}$", "description": "Уникальный префикс правой таблицы; base зарезервирован."},
                                "left_on": {"type": "array", "minItems": 1, "uniqueItems": True, "items": {"type": "string", "minLength": 1}, "description": "Ключи текущего результата с префиксом, например [base.customer_id]. Без префикса допустимо только однозначное точное имя."},
                                "right_on": {"type": "array", "minItems": 1, "uniqueItems": True, "items": {"type": "string", "minLength": 1}, "description": "Ключи правой таблицы без префикса в том же порядке, например [id]."},
                                "how": {"type": "string", "enum": list(JOIN_TYPES), "default": "left"},
                                "relationship": {"type": "string", "enum": list(JOIN_RELATIONSHIPS), "default": "many_to_one", "description": "Ожидаемая уникальность ключей слева и справа. Нарушение вызывает ошибку."},
                            },
                            "required": ["source_id", "alias", "left_on", "right_on"],
                            "additionalProperties": False,
                        },
                    },
                    "limit": {"type": "integer", "minimum": 1, "maximum": 1000, "default": 10},
                },
                "required": ["source_id", "joins"],
                "additionalProperties": False,
            },
        },
    },
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
            "description": "Получить структуру и статистику CSV-источника чата: число строк, названия и типы столбцов, пропуски, уникальные значения, среднее, минимум, максимум, медиану числовых столбцов и пять примеров строк. warnings содержит замечания о заголовках, числе полей и возможных ключах: сообщи о них пользователю и уточни неоднозначности. key_columns — исходные ключи, сохранённые строками. technical_id_column — созданный приложением ID строки, уникальный только внутри источника; это не бизнес-ключ. Используй, когда нужны эти сведения или названия столбцов для другого инструмента. Датасет подставляет приложение; source_id можно не указывать для активного источника.",
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
            "name": "get_rows_by_period",
            "description": "Получить строки CSV за период по столбцу с датой. Обе границы включены; end_date без времени включает весь последний день. Даты со смещением приводятся к UTC, даты без часового пояса считаются UTC. По умолчанию даты столбца должны быть ISO 8601; для другого формата явно задай date_format. Не угадывай неоднозначные даты. Пропуски и нераспознанные даты исключаются и считаются в missing_count и invalid_count; сообщи об исключениях пользователю. matched_count считается по всей таблице, rows содержит первые limit совпадений в исходном порядке, truncated указывает на неполную выдачу.",
            "parameters": {
                "type": "object",
                "properties": {
                    "column": {"type": "string", "minLength": 1, "description": "Точное название столбца с датой."},
                    "start_date": {"type": "string", "minLength": 1, "description": "Начало периода: YYYY-MM-DD или дата со временем ISO 8601."},
                    "end_date": {"type": "string", "minLength": 1, "description": "Конец периода: YYYY-MM-DD (весь день) или дата со временем ISO 8601 (включительно)."},
                    "date_format": {"type": "string", "minLength": 1, "default": "ISO8601", "description": "Формат дат в столбце: ISO8601 или явный шаблон, например %d.%m.%Y для 31.01.2026. Формат границ всегда ISO 8601."},
                    "limit": {"type": "integer", "minimum": 1, "maximum": 1000, "default": 10,
                              "description": "Сколько найденных строк показать."},
                },
                "required": ["column", "start_date", "end_date"],
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

tools.extend(PREPROCESSING_TOOLS)

# Start with read-only inspection, rather than making a transformation the first option.
tools.sort(key=lambda tool: tool["function"]["name"] not in ("list_sources", "read_dataset_and_gain_statistics"))

for tool in tools:
    if tool["function"]["name"] not in ("list_sources", "join_tables"):
        tool["function"]["parameters"]["properties"]["source_id"] = {
            "type": "string",
            "description": "ID CSV-источника из list_sources. Если не указан, используется активный источник чата.",
        }
