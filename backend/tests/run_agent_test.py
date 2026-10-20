import argparse
import base64
import binascii
import json
import os
import time
from dotenv import dotenv_values
from datetime import datetime
from pathlib import Path
import scenarios
import requests

URL = os.getenv("TEST_BASE_URL", "http://127.0.0.1:8080").rstrip("/")
env_path = Path(__file__).resolve().parents[1] / ".env"
test_settings = dotenv_values(env_path)
KEY = test_settings.get("BACKEND_KEY", "")
backend_timeout = float(os.getenv("REQUEST_TIMEOUT_SECONDS", test_settings.get("REQUEST_TIMEOUT_SECONDS") or "300"))
max_tool_calls = int(os.getenv("MAX_TOOL_CALLS", test_settings.get("MAX_TOOL_CALLS") or "5"))
# One summary request, up to N tool rounds, then the final answer.
READ_TIMEOUT = float(os.getenv("TEST_READ_TIMEOUT_SECONDS", str((max_tool_calls + 2) * backend_timeout + 30)))
TESTS = Path(__file__).resolve().parent
LOGS = TESTS / "logs"

def save_charts(body, log_path):
    """Keep metadata in the JSON and save image bytes next to that log."""
    errors = []
    if not isinstance(body, dict):
        return errors
    charts = body.get("charts", [])
    if not isinstance(charts, list):
        return ["response.charts должен быть списком"]
    for index, chart in enumerate(charts):
        if not isinstance(chart, dict):
            errors.append(f"charts[{index}] должен быть объектом")
            continue
        encoded = chart.pop("image_base64", None)
        try:
            if chart.get("mime_type") != "image/png":
                raise ValueError("ожидается mime_type=image/png")
            if not isinstance(encoded, str):
                raise ValueError("отсутствует image_base64")
            png = base64.b64decode(encoded, validate=True)
            if not png.startswith(b"\x89PNG\r\n\x1a\n"):
                raise ValueError("неверная сигнатура PNG")
            image_path = log_path.with_name(f"{log_path.stem}_{index}.png")
            image_path.write_bytes(png)
            chart["image_file"] = image_path.name
        except (ValueError, binascii.Error, OSError) as error:
            chart["image_error"] = str(error)
            errors.append(f"charts[{index}]: {error}")
    return errors


def run_scenario(scenario, context=None, *, skip_reason=None):
    payload = {
        "message": scenario["message"],
        "context": context if context is not None else [],
    }

    result = {
        "scenario": scenario["name"],
        "expected": scenario["expected"],
        "started_at": datetime.now().astimezone().isoformat(),
        "url": f"{URL}/agent/response",
        "request": payload,
        "file": scenario.get("file"),
        "status_code": None,
        "response": None,
        "error": None,
        "document_test": scenario.get("document_test"),
        "kind": scenario.get("kind"),
    }

    start = time.perf_counter()
    LOGS.mkdir(exist_ok=True)
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S_%f")
    log_path = LOGS / f"{scenario['name']}_{timestamp}.json"

    try:
        if skip_reason:
            result["skipped"] = True
            raise ValueError(skip_reason)
        files = None

        if scenario.get("file"):
            file_path = TESTS / scenario["file"]

            files = {
                "file": (
                    file_path.name,
                    file_path.read_bytes(),
                    "text/csv",
                )
            }

        response = requests.post(
            result["url"],
            headers={"BACKEND_KEY": KEY} if KEY else {},
            data={"payload": json.dumps(payload, ensure_ascii=False)},
            files=files,
            timeout=(5, READ_TIMEOUT),
        )

        result["status_code"] = response.status_code
        result["response"] = response.text

        try:
            result["response"] = response.json()
        except ValueError:
            pass

        response.raise_for_status()

    except (requests.RequestException, ValueError, OSError) as error:
        result["error"] = str(error)

    result["duration_seconds"] = round(time.perf_counter() - start, 3)

    image_errors = save_charts(result["response"], log_path)
    if image_errors:
        result["image_errors"] = image_errors

    text = json.dumps(result, ensure_ascii=False, indent=2)
    log_path.write_text(text, encoding="utf-8")

    print(text)
    print(f"\nЛог сохранён: {log_path}")

    if result["error"] is not None:
        return None

    body = result["response"]

    if isinstance(body, dict) and isinstance(body.get("context"), list):
        return body["context"]

    return None

def run_existing_scenarios():
    from scenarios import SCENARIOS, DIALOGUE, LONG_CONTEXT, LONG_SCENARIO, DATASET_DIALOGUE, ATTACK_SCENARIOS, DOCUMENT_ATTACK_SCENARIOS

    for scenario in SCENARIOS:
        run_scenario(scenario)

    print("\nПроверка связанного диалога")

    context = []

    for step in DIALOGUE:
        context = run_scenario(step, context)

        if context is None:
            print("Диалог остановлен: не получен контекст для продолжения.")
            break

    print("\nПроверка длинного контекста")

    context_size = sum(
        len(message["content"]) for message in LONG_CONTEXT
    )
    print(f"Размер истории: {context_size} символов")

    run_scenario(LONG_SCENARIO, LONG_CONTEXT)

    print("Проверка диалога по датасету")

    context = []

    for step in DATASET_DIALOGUE:
        context = run_scenario(step, context)

        if context is None:
            print("Диалог остановлен: не получен контекст.")
            break

    print("Проверка атак")

    for scenario in ATTACK_SCENARIOS:
        run_scenario(
            scenario,
            context=scenario.get("context"),
        )

    for scenario in DOCUMENT_ATTACK_SCENARIOS:
        run_scenario(scenario, context=[])


def run_chart_scenarios():
    if not hasattr(scenarios, "CHART_SCENARIOS"):
        raise SystemExit("Сначала выполните: py -3.12 tests/prepare_chart_dataset.py")
    print("Проверка графиков")
    context = None
    for scenario in scenarios.CHART_SCENARIOS:
        followup = scenario.get("use_previous_context", False)
        reason = None
        if followup and not context:
            reason = "Нет контекста предыдущего ответа: проверка без вложения пропущена."
        context = run_scenario(scenario, context if followup else [], skip_reason=reason)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Сценарии API агента с JSON-логами и PNG.")
    parser.add_argument("--suite", choices=("all", "charts", "existing"), default="all")
    args = parser.parse_args()
    if args.suite in ("all", "existing"):
        run_existing_scenarios()
    if args.suite in ("all", "charts"):
        run_chart_scenarios()
