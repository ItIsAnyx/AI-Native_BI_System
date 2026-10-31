"""Keep the first tool menu small for recognized metric families, with SQL fallback.

Routing never selects columns, dates, thresholds or answers: the model supplies them.
After a failed specialized calculation the full menu becomes available for recovery.
"""
import re
from app.tools.tools import MODEL_TOOLS

RULES = {
    "duration_percentile": r"перцентил|percentile|\bp(?:90|95|99)\b|квантил|quantile",
    "analyze_retry_chains": r"цепоч|retry|retries|повторн\w* попыт",
    "as_of_balance": r"(?:согласован|approved).*(?:оплач|paid)|(?:остат|balance).*(?:на конец|as of)",
    "compare_period_metrics": r"(?:вырос|рост|growth|increas).*(?:процент|%|percent)|(?:процент|percent).*(?:вырос|рост|growth|increas)",
}

def select_model_tools(question, executions):
    families={name for name,pattern in RULES.items() if re.search(pattern,question,re.I|re.S)}
    if "compare_period_metrics" in families:
        if re.search(r"выручк|revenue",question,re.I):
            families.remove("compare_period_metrics")
            families.add("compare_net_revenue")
        elif re.search(r"среднеднев|daily.*(?:per|average)|average.*daily",question,re.I):
            families.remove("compare_period_metrics")
            families.add("compare_daily_sales")
    if not families or sum(item["name"] in families and "error" in item["result"] for item in executions) >= 2:
        return MODEL_TOOLS
    common={"list_sources","get_dataset_columns","read_dataset_and_gain_statistics"}
    if re.search(r"график|диаграм|дашборд|визуализ|\bchart|dashboard|\bplot",question,re.I):
        common |= {"build_chart","build_dashboard"}
    return [tool for tool in MODEL_TOOLS if tool["function"]["name"] in common | families]
