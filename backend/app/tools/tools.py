tools = [
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
