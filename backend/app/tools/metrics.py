"""Parameterized business calculations; all source columns and conditions are caller supplied."""
import pandas as pd
import re

from app.tools.preprocessing import _columns, _numeric, _validate
from app.tools.query import query_dataset


def identifier(value):
    return '"' + value.replace('"', '""') + '"'


def literal(value):
    return "'" + value.replace("'", "''") + "'"


def boundary(value):
    if not isinstance(value, str):
        raise ValueError("Укажите границу периода в ISO 8601")
    try:
        timestamp = pd.Timestamp(value)
    except (ValueError, TypeError) as exc:
        raise ValueError("Некорректная дата периода") from exc
    if pd.isna(timestamp) or timestamp.tzinfo is not None:
        raise ValueError("Укажите локальную дату/время источника без смещения; например 2025-03-01")
    return "TIMESTAMP " + literal(timestamp.isoformat(sep=" "))


def timestamp(column):
    return "TRY_CAST(" + identifier(column) + " AS TIMESTAMP)"


def reporting_period(value):
    """A calendar month or an inclusive date range, converted to exact SQL boundaries."""
    if isinstance(value,str) and re.fullmatch(r"\d{4}-\d{2}",value):
        start=pd.Timestamp(value+"-01")
        return start.strftime("%Y-%m-%d"),(start+pd.offsets.MonthBegin(1)).strftime("%Y-%m-%d")
    if isinstance(value,str) and re.fullmatch(r"\d{4}-\d{2}-\d{2}/\d{4}-\d{2}-\d{2}",value):
        first,last=value.split("/")
        start,end=pd.Timestamp(first),pd.Timestamp(last)
        if start>end: raise ValueError("Начало периода позже конца")
        return first,(end+pd.Timedelta(days=1)).strftime("%Y-%m-%d")
    raise ValueError("Период: YYYY-MM для полного месяца или YYYY-MM-DD/YYYY-MM-DD, включая обе даты")


def checked(df, columns, numeric=()):
    _validate(df, 100)
    _columns(df, list(dict.fromkeys(c for c in columns if c is not None)))
    for column in numeric:
        if column: _numeric(df, column, protect_keys=True)


def required_columns(*columns):
    if any(not isinstance(column,str) or not column.strip() for column in columns):
        raise ValueError("Все обязательные столбцы должны быть заданы непустыми названиями из схемы источника")


def finish(df, sql, operation, limit, labels=None):
    result = query_dataset(df, sql, limit)
    result["operation"] = operation
    result["column_labels"] = labels or {}
    return result


def compare_period_metrics(df, group_by, date_column, value_column, baseline_start=None, baseline_end=None,
                           comparison_start=None, comparison_end=None, multiply_by_column=None, discount_percent_column=None,
                           normalization="none", entity_column=None, top_n=1, limit=100,baseline_period=None,comparison_period=None):
    required_columns(date_column,value_column)
    if baseline_period is not None:
        if baseline_start is not None or baseline_end is not None: raise ValueError("Задайте один способ выбора базового периода")
        baseline_start,baseline_end=reporting_period(baseline_period)
    if comparison_period is not None:
        if comparison_start is not None or comparison_end is not None: raise ValueError("Задайте один способ выбора сравниваемого периода")
        comparison_start,comparison_end=reporting_period(comparison_period)
    checked(df, [*group_by, date_column, value_column, multiply_by_column, discount_percent_column, entity_column],
            [value_column,multiply_by_column,discount_percent_column])
    _columns(df,group_by)
    if normalization not in {"none", "per_calendar_day_per_entity"}:
        raise ValueError("normalization: none или per_calendar_day_per_entity")
    if normalization != "none" and not entity_column:
        raise ValueError("Для нормирования на календарный день и организацию нужен entity_column")
    if normalization != "none" and entity_column in group_by:
        raise ValueError("entity_column — знаменатель среднего по всем организациям; его нельзя включать в group_by. "
                         "В group_by передайте только идентификатор и название сравниваемого товара/объекта, без организации.")
    if type(top_n) is not int or not 1 <= top_n <= 1000:
        raise ValueError("top_n: от 1 до 1000")
    b0,b1,c0,c1=map(boundary,[baseline_start,baseline_end,comparison_start,comparison_end])
    bd=(pd.Timestamp(baseline_end)-pd.Timestamp(baseline_start)).total_seconds()/86400
    cd=(pd.Timestamp(comparison_end)-pd.Timestamp(comparison_start)).total_seconds()/86400
    if bd<=0 or cd<=0: raise ValueError("Начало каждого периода должно предшествовать его концу; конец исключается")
    if normalization!="none" and (not bd.is_integer() or not cd.is_integer() or any(pd.Timestamp(v).time()!=pd.Timestamp(v).normalize().time() for v in [baseline_start,baseline_end,comparison_start,comparison_end])):
        raise ValueError("Для календарного среднего задайте границы полных дней")
    keys=", ".join(map(identifier,group_by))
    value=identifier(value_column)
    if multiply_by_column: value=f"({value} * {identifier(multiply_by_column)})"
    if discount_percent_column: value=f"({value} * (1-{identifier(discount_percent_column)}/100.0))"
    date=timestamp(date_column)
    entities=f"(SELECT COUNT(DISTINCT {identifier(entity_column)}) FROM dataset)" if entity_column else "1"
    normalized=normalization!="none"
    base_rate="baseline_total/(baseline_days*entity_count)" if normalized else "baseline_total"
    current_rate="comparison_total/(comparison_days*entity_count)" if normalized else "comparison_total"
    sql=f"""WITH totals AS (
      SELECT {keys}, SUM(CASE WHEN {date}>={b0} AND {date}<{b1} THEN {value} ELSE 0 END) AS baseline_total,
      SUM(CASE WHEN {date}>={c0} AND {date}<{c1} THEN {value} ELSE 0 END) AS comparison_total,
      COUNT(*) FILTER(WHERE {date}>={b0} AND {date}<{b1}) AS baseline_rows,
      COUNT(*) FILTER(WHERE {date}>={c0} AND {date}<{c1}) AS comparison_rows,
      {bd} AS baseline_days,{cd} AS comparison_days,{entities} AS entity_count
      FROM dataset GROUP BY {keys}), rates AS (
      SELECT *, {base_rate} AS baseline_rate,{current_rate} AS comparison_rate FROM totals)
      SELECT *,100.0*(comparison_rate/NULLIF(baseline_rate,0)-1) AS growth_percent
      FROM rates WHERE baseline_rate>0 ORDER BY growth_percent DESC LIMIT {top_n}"""
    result=finish(df,sql,"compare_period_metrics",limit,{
        "baseline_total":"Базовый период: всего","comparison_total":"Сравниваемый период: всего",
        "baseline_rows":"Строк в базовом периоде","comparison_rows":"Строк в сравниваемом периоде",
        "baseline_days":"Дней в базовом периоде","comparison_days":"Дней в сравниваемом периоде",
        "entity_count":"Организаций в знаменателе","baseline_rate":"Базовый показатель",
        "comparison_rate":"Сравниваемый показатель","growth_percent":"Рост, %"})
    result["method"]={"baseline_start":baseline_start,"baseline_end_exclusive":baseline_end,
                      "comparison_start":comparison_start,"comparison_end_exclusive":comparison_end,
                      "normalization":normalization,"entity_population":"all distinct nonnull entities in source; absent days contribute zero"}
    result["calculation_note"] = (f"Базовый период: {baseline_start} — {baseline_end}; сравниваемый: {comparison_start} — {comparison_end}. Концы периодов не включаются. "
        + ("Среднее = сумма / число календарных дней / число организаций; дни без продаж дают ноль. " if normalized else "Показатель = сумма значений" + (" × цена" if multiply_by_column else "") + (" × (1 − скидка / 100)" if discount_percent_column else "") + ". Знак количества сохраняется. ")
        + "Рост = (сравниваемый показатель / базовый показатель − 1) × 100%. Группы с неположительной базой исключены.")
    return result


def duration_percentile(df, group_column, start_column, end_column, period_start=None, period_end=None,
                        quantile=.9, min_count=1, clamp_zero=False, date_column=None, top_n=1, limit=100,period=None):
    if period is not None:
        if period_start is not None or period_end is not None: raise ValueError("Задайте один способ выбора периода")
        period_start,period_end=reporting_period(period)
    date_column=date_column or end_column
    required_columns(group_column,start_column,end_column,date_column)
    checked(df,[group_column,start_column,end_column,date_column])
    if isinstance(quantile,bool) or not isinstance(quantile,(int,float)) or not 0<quantile<1:
        raise ValueError("quantile должен быть между 0 и 1; P90=0.9, P95=0.95")
    if type(min_count) is not int or min_count<1 or type(top_n) is not int or not 1<=top_n<=1000 or type(clamp_zero) is not bool:
        raise ValueError("Проверьте min_count, top_n и clamp_zero")
    p0,p1=boundary(period_start),boundary(period_end)
    if pd.Timestamp(period_start)>=pd.Timestamp(period_end): raise ValueError("Некорректные границы периода")
    delta=f"epoch({timestamp(end_column)}-{timestamp(start_column)})/3600.0"
    metric=f"greatest({delta},0)" if clamp_zero else delta
    validity="TRUE" if clamp_zero else f"{timestamp(end_column)}>={timestamp(start_column)}"
    sql=f"""WITH intervals AS (SELECT {identifier(group_column)}, {metric} AS hours FROM dataset
      WHERE {timestamp(date_column)}>={p0} AND {timestamp(date_column)}<{p1}
      AND {timestamp(start_column)} IS NOT NULL AND {timestamp(end_column)} IS NOT NULL AND {validity})
      SELECT {identifier(group_column)}, COUNT(*) AS observation_count,
      COUNT(*) FILTER(WHERE hours=0) AS zero_count,quantile_cont(hours,{float(quantile)}) AS percentile_hours
      FROM intervals GROUP BY {identifier(group_column)} HAVING COUNT(*)>={min_count}
      ORDER BY percentile_hours DESC LIMIT {top_n}"""
    result=finish(df,sql,"duration_percentile",limit,{"observation_count":"Наблюдений","zero_count":"С нулевой длительностью",
        "percentile_hours":f"P{float(quantile)*100:g}, часы"})
    result["method"]={"start_column":start_column,"end_column":end_column,"date_column":date_column,
        "period_start":period_start,"period_end_exclusive":period_end,"quantile":quantile,"min_count":min_count,
        "clamp_zero":clamp_zero,"quantile_method":"linear PERCENTILE_CONT; numeric hours"}
    result["calculation_note"] = (f"Отбор: {date_column} с {period_start} до {period_end} (конец не включается). "
        f"Длительность: {end_column} − {start_column}, в часах. "
        + ("Ранние и своевременные доставки учтены с нулевой задержкой. " if clamp_zero else "Отрицательные длительности исключены. ")
        + f"Линейный P{float(quantile)*100:g}; минимум наблюдений в группе: {min_count}.")
    return result


def compare_net_revenue(df,group_by,date_column,quantity_column,unit_price_column,discount_percent_column,
                        baseline_period,comparison_period,top_n=1,limit=100):
    required_columns(quantity_column,unit_price_column,discount_percent_column)
    result=compare_period_metrics(df,group_by,date_column,quantity_column,
        multiply_by_column=unit_price_column,discount_percent_column=discount_percent_column,
        baseline_period=baseline_period,comparison_period=comparison_period,top_n=top_n,limit=limit)
    result["operation"]="compare_net_revenue"
    return result


def compare_daily_sales(df,item_id_column,item_name_column,date_column,sales_column,entity_column,
                        baseline_period,comparison_period,top_n=1,limit=100):
    required_columns(item_id_column,item_name_column,entity_column)
    group_by=list(dict.fromkeys([item_id_column,item_name_column]))
    result=compare_period_metrics(df,group_by,date_column,sales_column,entity_column=entity_column,
        normalization="per_calendar_day_per_entity",baseline_period=baseline_period,
        comparison_period=comparison_period,top_n=top_n,limit=limit)
    result["operation"]="compare_daily_sales"
    return result


def as_of_balance(df, group_column, approved_amount_column, approved_date_column, paid_amount_column,
                   paid_date_column, as_of_date, cancelled_date_column, rejected_date_column, limit=100):
    required_columns(group_column,approved_amount_column,approved_date_column,paid_amount_column,paid_date_column,
                     cancelled_date_column,rejected_date_column)
    checked(df,[group_column,approved_amount_column,approved_date_column,paid_amount_column,paid_date_column,
                cancelled_date_column,rejected_date_column],[approved_amount_column,paid_amount_column])
    if not isinstance(as_of_date,str) or len(as_of_date)!=10: raise ValueError("as_of_date: YYYY-MM-DD, включая весь день")
    cutoff=boundary((pd.Timestamp(as_of_date)+pd.Timedelta(days=1)).strftime("%Y-%m-%d"))
    filters=[f"{timestamp(approved_date_column)}<{cutoff}"]
    for column in [cancelled_date_column,rejected_date_column]:
        if column: filters.append(f"({timestamp(column)} IS NULL OR {timestamp(column)}>={cutoff})")
    approved=f"CAST({identifier(approved_amount_column)} AS DECIMAL(20,2))"
    paid=f"CASE WHEN {timestamp(paid_date_column)}<{cutoff} THEN CAST({identifier(paid_amount_column)} AS DECIMAL(20,2)) ELSE 0 END"
    sql=f"""WITH balances AS (SELECT {identifier(group_column)},{approved} AS approved_amount,
       {paid} AS paid_amount,{approved}-({paid}) AS outstanding FROM dataset WHERE {' AND '.join(filters)})
       SELECT {identifier(group_column)},COUNT(*) AS request_count,SUM(approved_amount) AS approved_rub,
       SUM(paid_amount) AS paid_as_of_rub,SUM(outstanding) AS outstanding_rub FROM balances WHERE outstanding>0
       GROUP BY {identifier(group_column)} ORDER BY {identifier(group_column)}"""
    result=finish(df,sql,"as_of_balance",limit,{"request_count":"Заявок","approved_rub":"Согласовано, руб.",
        "paid_as_of_rub":"Оплачено на дату, руб.","outstanding_rub":"Не оплачено на дату, руб."})
    result["method"]={"as_of_date_inclusive":as_of_date,
                      "cancelled_date_column":cancelled_date_column,"rejected_date_column":rejected_date_column,
                      "payment_rule":"Only payments whose event date precedes the cutoff reduce the historical balance."}
    result["calculation_note"] = (f"На конец {as_of_date}: согласованная сумма минус оплата, совершённая к этой дате. "
        + (f"Отмена учитывается по столбцу {cancelled_date_column}. " if cancelled_date_column else "Исключение отменённых не задано. ")
        + (f"Отклонение учитывается по столбцу {rejected_date_column}. " if rejected_date_column else "Исключение отклонённых не задано. ")
        + "Показаны только положительные остатки.")
    return result


def analyze_retry_chains(df, task_column, chain_column, attempt_column, status_column, success_value="Успешно", limit=100):
    required_columns(task_column,chain_column,attempt_column,status_column)
    checked(df,[task_column,chain_column,attempt_column,status_column],[attempt_column])
    if not isinstance(success_value,str) or not success_value: raise ValueError("Укажите значение статуса успеха")
    statuses=df[status_column].dropna().unique().tolist()
    if success_value not in statuses:
        raise ValueError("Указанный статус успеха отсутствует в источнике. Фактические значения: "
                         + ", ".join(str(value)[:80] for value in statuses[:20]))
    if df[[task_column,chain_column,attempt_column,status_column]].isna().any().any():
        raise ValueError("В полях цепочки есть пропуски; уточните правила обработки неполной истории")
    if df.duplicated([task_column,chain_column,attempt_column]).any():
        raise ValueError("Номер попытки внутри цепочки повторяется; уточните порядок событий")
    attempts=df[attempt_column]
    if (attempts<1).any() or (attempts%1!=0).any(): raise ValueError("Номера попыток должны быть положительными целыми")
    task,chain,attempt,status=map(identifier,[task_column,chain_column,attempt_column,status_column])
    sql=f"""WITH chains AS (SELECT {task},{chain},COUNT(*) AS attempts,MIN({attempt}) AS first_attempt,
      MAX({attempt}) AS last_attempt,arg_max({status},{attempt}) AS final_status,
      COUNT(*) FILTER(WHERE {status}={literal(success_value)}) AS successes FROM dataset GROUP BY {task},{chain}),
      classified AS (SELECT *,final_status={literal(success_value)} AND attempts>1 AND successes=1 AS recovered FROM chains)
      SELECT {task},COUNT(*) AS total_chains,COUNT(*) FILTER(WHERE recovered) AS successful_after_retry,
      100.0*COUNT(*) FILTER(WHERE recovered)/COUNT(*) AS share_of_all_chains_percent,
      AVG(attempts) FILTER(WHERE recovered) AS mean_attempts_in_recovered_chains,
      COUNT(*) FILTER(WHERE first_attempt<>1 OR last_attempt<>attempts) AS incomplete_chains
      FROM classified GROUP BY {task} ORDER BY share_of_all_chains_percent DESC"""
    result=finish(df,sql,"analyze_retry_chains",limit,{"total_chains":"Всего цепочек","successful_after_retry":"Успех после повторов",
        "share_of_all_chains_percent":"Доля всех цепочек, %","mean_attempts_in_recovered_chains":"Среднее попыток, включая первую",
        "incomplete_chains":"Цепочек с неполной историей"})
    if any(row["incomplete_chains"] for row in result["rows"]):
        result["source_warnings"].append("Есть цепочки с неполной историей; расчёт относится только к наблюдаемым попыткам.")
    result["method"]={"denominator":"all observed chains by task", "success_rule":"terminal success after multiple attempts, no earlier success",
                      "mean_attempts":"includes the initial attempt"}
    result["calculation_note"] = ("Доля = цепочки с успехом на последней попытке после повторов / все цепочки задания × 100%. "
        "Более ранних успешных попыток в таких цепочках нет. Среднее число попыток включает первую.")
    return result


def tool(name,description,properties,required):
    return {"type":"function","function":{"name":name,"description":description,"parameters":{
        "type":"object","properties":properties,"required":required,"additionalProperties":False}}}

S={"type":"string","minLength":1}
METRIC_FUNCTIONS={f.__name__:f for f in [compare_period_metrics,compare_net_revenue,compare_daily_sales,duration_percentile,as_of_balance,analyze_retry_chains]}
METRIC_TOOLS=[
 tool("compare_period_metrics","Сравнить рост показателя между двумя периодами по группам. Для выручки value_column=количество (с исходным знаком), multiply_by_column=цена, discount_percent_column=скидка в процентах. Для среднедневного значения на организацию normalization=per_calendar_day_per_entity, entity_column=ID организации: используется весь календарь, включая отсутствующие/нулевые дни. Даты окончания исключаются. Возвращает суммы, знаменатели, средние и процент роста, отсортированные по убыванию.",
      {**{k:S for k in ["date_column","value_column","multiply_by_column","discount_percent_column","entity_column"]},
       **{k:{"type":"string","description":"YYYY-MM для полного месяца, например 2025-03; либо YYYY-MM-DD/YYYY-MM-DD, включая обе даты"} for k in ["baseline_period","comparison_period"]},
       "group_by":{"type":"array","minItems":1,"items":S,"description":"Идентификатор и читаемое название сравниваемого объекта, например ID товара + название. entity_column сюда НЕ включать: по нему считается среднее, это знаменатель."},"normalization":{"type":"string","enum":["none","per_calendar_day_per_entity"]},
       "top_n":{"type":"integer","minimum":1,"maximum":1000,"default":1}},
      ["group_by","date_column","value_column","baseline_period","comparison_period"]),
 tool("duration_percentile","P90/P95 длительности в ЧАСАХ по группам за период. Для времени решения обращения start_column=создано, end_column=закрыто (не первый ответ). Для задержки доставки start_column=обещанный срок,end_column=доставлено,clamp_zero=true. Отбор по date_column (по умолчанию end_column), min_count после отбора. Конец периода исключается. top_n=1 для максимума.",
      {**{k:S for k in ["group_column","start_column","end_column","date_column"]},
       "period":{"type":"string","description":"Отчётный месяц YYYY-MM, например 2025-03 — весь март; либо YYYY-MM-DD/YYYY-MM-DD, включая обе даты"},
       "quantile":{"type":"number","exclusiveMinimum":0,"exclusiveMaximum":1},"min_count":{"type":"integer","minimum":1,"default":1},
       "clamp_zero":{"type":"boolean","default":False},"top_n":{"type":"integer","minimum":1,"maximum":1000,"default":1}},
      ["group_column","start_column","end_column","period","quantile"]),
 tool("as_of_balance","Исторический неоплаченный остаток согласованных сумм на конец дня YYYY-MM-DD по группам. Согласование до границы, оплата только если произошла к той дате; отмена и отклонение исключаются только если уже произошли. Не использует текущий статус. Возвращает количество и денежные суммы.",
      {k:S for k in ["group_column","approved_amount_column","approved_date_column","paid_amount_column","paid_date_column","as_of_date","cancelled_date_column","rejected_date_column"]},
      ["group_column","approved_amount_column","approved_date_column","paid_amount_column","paid_date_column","as_of_date","cancelled_date_column","rejected_date_column"]),
 tool("analyze_retry_chains","Для каждого задания посчитать долю ВСЕХ цепочек с терминальным успехом только после повторных попыток и среднее число попыток в этих цепочках, включая первую. Группирует по task_column+chain_column и упорядочивает по attempt_column, не по строкам файла. Проверяет дубли и неполную историю.",
      {k:S for k in ["task_column","chain_column","attempt_column","status_column","success_value"]},
      ["task_column","chain_column","attempt_column","status_column"]),
]

PERIOD_PROPERTY={"type":"string","description":"Полный месяц YYYY-MM, например 2025-03, либо YYYY-MM-DD/YYYY-MM-DD включительно"}
GROUP_PROPERTY={"type":"array","minItems":1,"items":S,"description":"ID и читаемое название сравниваемого объекта. Для среднего по организациям не включай сюда entity_column."}
METRIC_TOOLS.extend([
 tool("compare_net_revenue","Рост ЧИСТОЙ ВЫРУЧКИ по группам между периодами: сумма(количество × цена за единицу × (1 − скидка в процентах / 100)). Знак количества сохраняется: отрицательные возвраты уменьшают выручку. Себестоимость не вычитается. Все три числовых столбца обязательны. Возвращает суммы обоих периодов и процент роста.",
      {**{k:S for k in ["date_column","quantity_column","unit_price_column","discount_percent_column"]},"group_by":GROUP_PROPERTY,
       "baseline_period":PERIOD_PROPERTY,"comparison_period":PERIOD_PROPERTY,"top_n":{"type":"integer","minimum":1,"maximum":1000,"default":1}},
      ["group_by","date_column","quantity_column","unit_price_column","discount_percent_column","baseline_period","comparison_period"]),
 tool("compare_daily_sales","Рост СРЕДНЕДНЕВНЫХ ПРОДАЖ НА ОРГАНИЗАЦИЮ по товарам/объектам между периодами. Среднее = сумма продаж / все календарные дни / число различных организаций в источнике. Дни без продаж дают ноль. Сравнивает объекты по их ID и названию, усредняет по всем организациям entity_column. Возвращает ID, название, суммы, дни, количество организаций, средние и процент роста.",
      {**{k:S for k in ["date_column","sales_column"]},
       "item_id_column":{"type":"string","description":"Столбец ID сравниваемого товара/объекта, не ID организации"},
       "item_name_column":{"type":"string","description":"Столбец названия сравниваемого товара; для препарата — действующее вещество, а не тип/категория или ID"},
       "entity_column":{"type":"string","description":"Столбец ID организаций, например аптек/магазинов, по всем которым вычисляется среднее"},
       "baseline_period":PERIOD_PROPERTY,"comparison_period":PERIOD_PROPERTY,"top_n":{"type":"integer","minimum":1,"maximum":1000,"default":1}},
      ["item_id_column","item_name_column","date_column","sales_column","entity_column","baseline_period","comparison_period"]),
])
