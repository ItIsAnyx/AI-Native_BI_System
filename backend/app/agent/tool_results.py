"""Present dataset results from executed tools rather than generated sample rows."""
import html
import json
import re


TABLE_TOOLS = {"group_dataset", "clean_missing_values", "drop_columns", "drop_duplicates",
               "filter_rows", "find_anomalies", "find_duplicates", "get_rows_by_period", "join_tables",
               "read_dataset_and_gain_statistics"}


def has_tool_markup(answer):
    return bool(re.search(r"<\s*(?:tool_call\b|function\s*=)", answer))


def _cell(value):
    if value is None:
        return "null"
    if isinstance(value, (dict, list)):
        value = json.dumps(value, ensure_ascii=False)
    text = html.escape(str(value), quote=False).replace("\r", " ").replace("\n", " ")
    return re.sub(r"([\\|`*_\[\]])", r"\\\1", text)


def _table(rows):
    if not rows:
        return []
    columns = list(dict.fromkeys(key for row in rows for key in row))
    return ["| " + " | ".join(_cell(key) for key in columns) + " |",
            "| " + " | ".join("---" for _ in columns) + " |",
            *("| " + " | ".join(_cell(row.get(key)) for key in columns) + " |" for row in rows)]


def render_tool_results(executions, russian=True):
    """Return a grounded answer for table tools, or None for other capabilities."""
    relevant = [item for item in executions if item["name"] in TABLE_TOOLS]
    if not relevant or any(item["name"] not in TABLE_TOOLS | {"list_sources"} for item in executions):
        return None
    tr = lambda ru, en: ru if russian else en
    successful = [item for item in relevant if "error" not in item["result"]]
    # A corrected retry replaces an earlier argument error for the same tool.
    unresolved = [item for index, item in enumerate(relevant) if "error" in item["result"] and not any(
        later["name"] == item["name"] and "error" not in later["result"]
        for later in relevant[index + 1:])]
    lines = []
    for item in unresolved[-1:]:
        lines += [tr("Операция не выполнена: ", "Operation failed: ") + _cell(item["result"]["error"]), ""]
    operations = [item for item in successful if item["name"] != "read_dataset_and_gain_statistics"]
    for item in operations:
        name, result = item["name"], item["result"]
        if name == "group_dataset":
            lines += [tr("Группировка", "Grouping") + f": {_cell(result['group_by'])}.",
                      tr("Групп: ", "Groups: ") + str(result["group_count"]) + "; "
                      + tr("строк учтено: ", "included rows: ") + str(result["included_rows"]) + "; "
                      + tr("исключено: ", "excluded: ") + str(result["excluded_rows"]) + ".",
                      tr("Агрегаты: ", "Aggregations: ") + _cell(result["aggregations"]), ""]
        elif name in {"clean_missing_values", "drop_columns", "drop_duplicates", "filter_rows"}:
            lines += [f"{name}: {result['input_rows']} → {result['total_rows']}; "
                      + tr("удалено строк: ", "removed rows: ") + str(result["removed_rows"]) + "."]
            details = {key: result[key] for key in ("strategy", "fill_values", "missing_before", "missing_after",
                       "removed_columns", "subset", "keep") if key in result}
            if name == "filter_rows":
                details.update({key: item["arguments"].get(key, default) for key, default in
                                (("conditions", []), ("combine", "all"), ("action", "keep"))})
            lines += [_cell(details), ""]
        elif name == "find_duplicates":
            lines += [tr("Проверено строк: ", "Checked rows: ") + str(result["total_rows"]) + ".",
                      tr("Столбцы сравнения: ", "Compared columns: ") + _cell(result["subset"]) + ".",
                      tr("Дополнительных повторов сверх первого: ", "Extra occurrences after the first: ") + str(result["duplicate_count"]) + ".",
                      tr("Строк в повторяющихся группах, включая первые: ", "Rows in duplicate groups, including the first: ")
                      + str(result["duplicate_rows_count"]) + "; "
                      + tr("групп: ", "groups: ") + str(result["duplicate_group_count"]) + ".",
                      tr("Данные не изменены.", "Data is unchanged."), ""]
        elif name == "find_anomalies":
            lines += [tr("Аномалий: ", "Anomalies: ") + str(result["anomaly_count"]) + ".",
                      tr("Границы и пропуски: ", "Bounds and missing values: ") + _cell(result["columns"]),
                      tr("Данные не изменены.", "Data is unchanged."), ""]
        elif name == "get_rows_by_period":
            lines += [f"{_cell(result['start_date'])} — {_cell(result['end_date'])} (UTC).",
                      tr("Совпадений: ", "Matches: ") + str(result["matched_count"]) + "; "
                      + tr("строк в исходнике: ", "source rows: ") + str(result["total_rows"]) + ".",
                      tr("Пропущенных дат: ", "Missing dates: ") + str(result["missing_count"]) + "; "
                      + tr("неверных дат: ", "invalid dates: ") + str(result["invalid_count"]) + ".", ""]
        elif name == "join_tables":
            lines += [tr("Объединение: ", "Join: ") + str(result["total_rows"]) + tr(" строк.", " rows."),
                      *_table(result["steps"]), ""]
    if successful:
        last = successful[-1]
        result = last["result"]
        if last["name"] == "read_dataset_and_gain_statistics":
            lines += [tr("Строк в источнике: ", "Source rows: ") + str(result["total_rows"]) + ".", ""]
            stats = [{"column": key, **value} for key, value in result["columns"].items()]
            lines += [*_table(stats), ""]
            rows = result["example_strings"]
            lines += [tr("Примеры строк (не вся таблица):", "Sample rows (not the whole table):"), ""]
        else:
            rows = result.get("rows", [])
            if last["name"] == "find_anomalies":
                rows = [{**row["values"], "anomaly_columns": row["anomaly_columns"]} for row in rows]
            if result.get("truncated"):
                lines += [tr("Показаны только первые ", "Showing only the first ") + str(result["returned_count"])
                          + tr(" строк; полный результат больше.", " rows; the full result is larger."), ""]
        lines += [*_table(rows)] if rows else [tr("Нет строк для отображения.", "No rows to display.")]
        if result.get("source_id"):
            lines += ["", tr("Источник: ", "Source: ") + _cell(result["source_id"])]
    warnings = list(dict.fromkeys(str(warning) for item in successful for key in ("warnings", "source_warnings")
                                 for warning in item["result"].get(key, [])))
    if warnings:
        lines += ["", tr("Замечания: ", "Notes: ") + " ".join(_cell(value) for value in warnings)]
    return "\n".join(lines).strip()
