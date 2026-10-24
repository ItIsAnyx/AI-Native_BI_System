from app.tools.preprocessing import FILTER_OPERATORS, MISSING_STRATEGIES


COLUMNS = {"type": "array", "minItems": 1, "uniqueItems": True, "items": {"type": "string", "minLength": 1}}
VALUE = {"type": ["string", "number", "boolean"]}
LIMIT = {"type": "integer", "minimum": 1, "maximum": 1000, "default": 10}


def _tool(name, description, properties, required):
    return {
        "type": "function",
        "function": {
            "name": name, "description": description,
            "parameters": {"type": "object", "properties": {**properties, "limit": LIMIT},
                           "required": required, "additionalProperties": False},
        },
    }


TRANSFORM_NOTE = (
    " Создаёт новый CSV-источник, исходник сохраняется. source_id результата используется дальше и становится активным. "
    "Обрабатывает всю таблицу; limit ограничивает только примеры. Сообщи размер результата и выполненные изменения. "
    "Применяй только запрошенную пользователем обработку; неоднозначные столбцы и правила сначала уточни."
)

PREPROCESSING_TOOLS = [
    _tool("clean_missing_values",
          "Обработать пропуски (null и пустые/пробельные строки) в выбранных столбцах. "
          "drop_rows удаляет строки с любым пропуском среди выбранных столбцов; constant заполняет заданным value; "
          "mean/median — средним/медианой числового показателя; mode — первой модой в порядке pandas. "
          "Если columns не заданы, используются все столбцы кроме технического ID. Среднее/медиана не применяются к идентификаторам. "
          "Типы автоматически не преобразуются, при отсутствии данных для расчёта заполнения возвращается ошибка." + TRANSFORM_NOTE,
          {"columns": COLUMNS, "strategy": {"type": "string", "enum": list(MISSING_STRATEGIES), "default": "drop_rows"},
           "value": {**VALUE, "description": "Только для constant: непустое значение подходящего типа."}}, []),
    _tool("drop_columns", "Удалить явно перечисленные столбцы; в таблице должен остаться хотя бы один столбец." + TRANSFORM_NOTE,
          {"columns": COLUMNS}, ["columns"]),
    _tool("drop_duplicates",
          "Удалить дубликаты строк по subset. По умолчанию сравниваются все столбцы кроме технического ID строки. "
          "keep=first сохраняет первое вхождение, last — последнее, none удаляет все вхождения повторяющейся группы." + TRANSFORM_NOTE,
          {"subset": COLUMNS, "keep": {"type": "string", "enum": ["first", "last", "none"], "default": "first"}}, []),
    _tool("find_duplicates",
          "Найти дубликаты без удаления и изменения данных. subset задаёт столбцы сравнения; "
          "по умолчанию сравниваются все столбцы кроме технического ID строки. "
          "Бизнес-идентификаторы автоматически не исключаются. Правила сравнения такие же, как у drop_duplicates, "
          "включая совпадения пропусков. duplicate_count — дополнительные повторы сверх первого в каждой группе; "
          "duplicate_rows_count — все строки повторяющихся групп, включая первые; duplicate_group_count — число таких групп. "
          "rows содержит первые limit строк повторяющихся групп в исходном порядке. Счётчики относятся ко всей таблице. "
          "Новый CSV не создаётся, активный источник не меняется. Удалять повторы можно только по отдельному запросу пользователя.",
          {"subset": COLUMNS}, []),
    _tool("find_anomalies",
          "Найти статистические аномалии в явно выбранных числовых показателях (не в идентификаторах). "
          "iqr: границы Q1−threshold*IQR и Q3+threshold*IQR, по умолчанию threshold=1.5, минимум 4 конечных значения. "
          "zscore: среднее ± threshold*стандартное отклонение (ddof=0), по умолчанию threshold=3, минимум 3 значения. "
          "Бесконечности считаются аномалиями, пропуски учитываются отдельно. Возвращает границы, число аномалий и примеры строк. "
          "Исходник не меняется. Сообщи warnings. Аномалия не обязательно ошибка; не удаляй её без запроса пользователя. "
          "Для удаления используй filter_rows с явными границами (строгие lt/gt, combine=any, action=remove), "
          "для бесконечностей добавь not_finite. limit ограничивает только примеры.",
          {"columns": COLUMNS, "method": {"type": "string", "enum": ["iqr", "zscore"], "default": "iqr"},
           "threshold": {"type": "number", "exclusiveMinimum": 0}}, ["columns"]),
    _tool("filter_rows",
          "Оставить (action=keep) или удалить (remove) строки по явно заданным условиям. "
          "combine=all означает И, any — ИЛИ. eq/ne/in/not_in сравнивают точные значения без преобразования типов. "
          "gt/ge/lt/le/between применяются к числам; between включает границы. "
          "is_null/not_null проверяют пропуски и пустые строки; is_finite/not_finite — конечность непустых чисел. "
          "Этим четырём операторам value не передаётся. Для in/not_in value — список, для between — [нижняя, верхняя]. "
          "Пропуски не совпадают с обычными условиями, в том числе ne/not_in. Для дат используй get_rows_by_period. "
          "Произвольный код и выражения не исполняются." + TRANSFORM_NOTE,
          {"conditions": {"type": "array", "minItems": 1, "maxItems": 50, "items": {
              "type": "object", "properties": {
                  "column": {"type": "string", "minLength": 1},
                  "operator": {"type": "string", "enum": list(FILTER_OPERATORS)},
                  "value": {"anyOf": [VALUE, {"type": "array", "minItems": 1, "maxItems": 1000, "items": VALUE}]},
              }, "required": ["column", "operator"], "additionalProperties": False,
          }}, "combine": {"type": "string", "enum": ["all", "any"], "default": "all"},
           "action": {"type": "string", "enum": ["keep", "remove"], "default": "keep"}}, ["conditions"]),
]
