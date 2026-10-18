import json
import os
import time
from dotenv import dotenv_values
from datetime import datetime
from pathlib import Path
from scenarios import SCENARIOS, DIALOGUE, LONG_CONTEXT, LONG_SCENARIO, DATASET_DIALOGUE, ATTACK_SCENARIOS
from scenarios import DOCUMENT_ATTACK_SCENARIOS
import requests

URL = os.getenv("TEST_BASE_URL", "http://127.0.0.1:8080").rstrip("/")
env_path = Path(__file__).resolve().parents[1] / ".env"
KEY = dotenv_values(env_path).get("BACKEND_KEY", "")

def run_scenario(scenario, context=None):
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

    try:
        if not KEY:
            raise ValueError("Надо задать TEST_BACKEND_KEY в настройках запуска!")

        files = None

        if scenario.get("file"):
            file_path = (
                    Path(__file__).resolve().parent / scenario["file"]
            )

            files = {
                "file": (
                    file_path.name,
                    file_path.read_bytes(),
                    "text/csv",
                )
            }

        response = requests.post(
            result["url"],
            headers={"BACKEND_KEY": KEY},
            data={"payload": json.dumps(payload, ensure_ascii=False)},
            files=files,
            timeout=(5, 330),
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

    logs = Path(__file__).resolve().parent / "logs"
    logs.mkdir(exist_ok=True)

    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S_%f")
    filename = f"{scenario['name']}_{timestamp}.json"
    log_path = logs / filename

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

if __name__ == "__main__":
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