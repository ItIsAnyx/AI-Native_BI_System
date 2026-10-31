import argparse
import base64
import binascii
import importlib
import json
import os
import re
import sys
import time
from dotenv import dotenv_values
from datetime import datetime
from pathlib import Path
from http.cookies import SimpleCookie
from urllib.parse import urlsplit
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

def run_existing_scenarios():
    import scenarios
    runner = ToolRunner()
    cases = []
    for name in ("SCENARIOS", "DIALOGUE", "DATASET_DIALOGUE", "ATTACK_SCENARIOS", "DOCUMENT_ATTACK_SCENARIOS"):
        group = getattr(scenarios, name, [])
        for index, case in enumerate(group):
            if case.get("context"):
                raise ValueError("Клиентский context больше не поддерживается. Перенесите историю в последовательность запросов.")
            cases.append({**case, "use_previous_context": name in {"DIALOGUE", "DATASET_DIALOGUE"} and index > 0})
    try:
        return runner.run(cases)
    finally:
        runner.session.close()


def run_chart_scenarios():
    import scenarios
    runner = ToolRunner()
    try:
        return runner.run(scenarios.CHART_SCENARIOS)
    finally:
        runner.session.close()


def prepare_tool_datasets():
    """Prepare CSV fixtures only; never contact the API or model."""
    module = importlib.import_module("scenarios")
    datasets = getattr(module, "TOOL_DATASETS", None)
    if not isinstance(datasets, dict) or not datasets:
        raise ValueError("Добавьте TOOL_DATASETS в tests/scenarios.py")
    pending = []
    for name, content in datasets.items():
        if not isinstance(name, str) or Path(name).name != name or not name.endswith(".csv"):
            raise ValueError("Имена контрольных файлов должны быть именами CSV без пути")
        path = (TESTS / "datasets" / name).resolve()
        if not path.is_relative_to((TESTS / "datasets").resolve()):
            raise ValueError("Контрольный CSV выходит за пределы datasets")
        if not isinstance(content, str):
            raise ValueError("Содержимое контрольного CSV должно быть строкой")
        if path.exists() and path.read_text(encoding="utf-8-sig") != content:
            raise ValueError(f"Файл уже существует с другими данными: {path}")
        if not path.exists():
            pending.append((path, content))
    for path, content in pending:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
    print(f"Контрольные CSV готовы: {len(datasets)}. Запросы не отправлялись.")


def select_tool_scenarios(cases, selected_names):
    if not selected_names:
        return cases
    requested = set(selected_names)
    unknown = requested - {case["name"] for case in cases}
    if unknown:
        raise ValueError(f"Неизвестные сценарии: {', '.join(sorted(unknown))}")
    selected, chain = set(), []
    for case in cases:
        if not case.get("use_previous_context"):
            chain = []
        chain.append(case["name"])
        if case["name"] in requested:
            selected.update(chain)
    return [case for case in cases if case["name"] in selected]


TOOL_SUITES = {'grouping': 'GROUPING_SCENARIOS',
 'preprocessing': 'PREPROCESSING_SCENARIOS',
 'period': 'PERIOD_SCENARIOS',
 'joins': 'JOIN_SCENARIOS',
 'duplicates': 'DUPLICATE_SCENARIOS',
 'time': 'TIME_SCENARIOS',
 'dashboards': 'DASHBOARD_SCENARIOS'}


def load_scenarios(suite):
    if suite == "smoke":
        from smoke_cases import prepare
        return prepare(TESTS)
    try:
        module = importlib.import_module("scenarios")
    except ModuleNotFoundError as exc:
        if exc.name != "scenarios":
            raise
        raise ValueError("Добавьте наборы сценариев в tests/scenarios.py") from exc
    selected = TOOL_SUITES if suite == "all" else {suite: TOOL_SUITES[suite]}
    cases = []
    for kind, variable in selected.items():
        group = getattr(module, variable, None)
        if not isinstance(group, list) or not group:
            raise ValueError(f"Нет {variable}; добавьте набор в tests/scenarios.py")
        cases.extend({**scenario, "kind": kind} for scenario in group)
    return cases


class ToolRunner:
    def __init__(self, root=TESTS):
        self.root = Path(root)
        settings = dotenv_values(self.root.parent / ".env")
        self.url = os.getenv("TEST_BASE_URL", "http://127.0.0.1:8080").rstrip("/")
        backend_timeout = float(os.getenv("REQUEST_TIMEOUT_SECONDS", settings.get("REQUEST_TIMEOUT_SECONDS") or "300"))
        max_calls = int(os.getenv("MAX_TOOL_CALLS", settings.get("MAX_TOOL_CALLS") or "5"))
        self.timeout = (5, float(os.getenv("TEST_READ_TIMEOUT_SECONDS", str((max_calls + 2) * backend_timeout + 30))))
        self.session = requests.Session()
        self.results = []
        self.logs = self.root / "logs" / ("tools_" + datetime.now().strftime("%Y-%m-%d_%H-%M-%S_%f"))

    def authenticate(self):
        cookie = os.getenv("TEST_COOKIE", "")
        email, password = os.getenv("TEST_EMAIL", ""), os.getenv("TEST_PASSWORD", "")
        if cookie:
            parsed = SimpleCookie()
            parsed.load(cookie)
            if not parsed:
                raise ValueError("TEST_COOKIE не содержит cookies")
            for name, item in parsed.items():
                self.session.cookies.set(name, item.value, domain=urlsplit(self.url).hostname, path="/")
        elif email and password:
            response = self.session.post(self.url + "/api/auth/login", json={"email": email, "password": password}, timeout=(5, 30))
            response.raise_for_status()
        else:
            raise ValueError("Задайте TEST_EMAIL и TEST_PASSWORD тестового аккаунта либо TEST_COOKIE. Учётные данные в логи не записываются.")

    def request(self, method, path, **kwargs):
        response = getattr(self.session, method)(self.url + path, **kwargs)
        if response.status_code == 401:
            refreshed = self.session.post(self.url + "/api/auth/refresh", timeout=(5, 30))
            refreshed.raise_for_status()
            response = getattr(self.session, method)(self.url + path, **kwargs)
        return response

    def dataset_path(self, relative):
        if not isinstance(relative, str):
            raise ValueError("file должен быть относительным путём к CSV")
        path = (self.root / relative).resolve()
        if not path.is_relative_to((self.root / "datasets").resolve()) or path.suffix.lower() != ".csv":
            raise ValueError("Файлы тестов должны находиться в tests/datasets и иметь расширение .csv")
        if not path.is_file():
            raise ValueError(f"Не найден {path}; выполните tests/run_agent_test.py --prepare")
        return path

    def validate_cases(self, cases):
        names = set()
        for scenario in cases:
            name = scenario.get("name")
            if not isinstance(name, str) or not re.fullmatch(r"[A-Za-z0-9_]+", name) or name in names:
                raise ValueError("Имена сценариев должны быть уникальными и содержать только латинские буквы, цифры и _")
            names.add(name)
            for item in [scenario, *scenario.get("setup_files", [])]:
                if item.get("file"):
                    self.dataset_path(item["file"])
            if not scenario.get("message") or not scenario.get("expected"):
                raise ValueError(f"В {name} не заданы message/expected")

    def save_charts(self, body, log_path):
        errors = []
        charts = body.get("charts", [])
        if not isinstance(charts, list):
            return ["charts должен быть списком"]
        for index, chart in enumerate(charts):
            try:
                if not isinstance(chart, dict):
                    raise ValueError("chart должен быть объектом")
                encoded = chart.pop("image_base64", None)
                if encoded is not None:
                    if not isinstance(encoded, str):
                        raise ValueError("image_base64 должен быть строкой")
                    data = base64.b64decode(encoded, validate=True)
                else:
                    url = chart.get("url", "")
                    if not isinstance(url, str) or not re.fullmatch(r"/agent/artifacts/[0-9a-fA-F-]{36}", url):
                        raise ValueError("Некорректный URL артефакта")
                    response = self.request("get", url, timeout=self.timeout)
                    response.raise_for_status()
                    data = response.content
                if chart.get("mime_type") != "image/png" or not data.startswith(b"\x89PNG\r\n\x1a\n"):
                    raise ValueError("Ожидается PNG")
                path = log_path.with_name(f"{log_path.stem}_{index}.png")
                path.write_bytes(data)
                chart["image_file"] = path.name
            except (ValueError, OSError, requests.RequestException) as exc:
                errors.append(str(exc))
        return errors

    def run_scenario(self, scenario, state=None, skip_reason=None):
        state = state or {"chat_id": None, "sources": [], "aliases": {}}
        payload = {"message": scenario["message"]}
        result = {"scenario": scenario["name"], "kind": scenario.get("kind"), "expected": scenario["expected"],
                  "started_at": datetime.now().astimezone().isoformat(), "url": self.url + "/agent/response",
                  "request": payload, "file": scenario.get("file"), "status_code": None,
                  "response": None, "error": None, "evaluation": "not_run"}
        self.logs.mkdir(parents=True, exist_ok=True)
        path = self.logs / (f"{len(self.results) + 1:03d}_" + scenario["name"] + ".json")
        start = time.perf_counter()
        next_state = None
        try:
            if skip_reason:
                result["skipped"] = True
                raise ValueError(skip_reason)
            aliases = state["aliases"]
            payload["message"] = re.sub(r"\{\{([A-Za-z0-9_]+)\}\}", lambda match: aliases[match[1]], payload["message"])
            if state["chat_id"]:
                payload["chat_id"] = state["chat_id"]
            if scenario.get("source_alias"):
                payload["source_id"] = aliases[scenario["source_alias"]]
            files = None
            if scenario.get("file"):
                csv = self.dataset_path(scenario["file"])
                files = {"file": (csv.name, csv.read_bytes(), "text/csv")}
            response = self.request("post", "/agent/response", data={"payload": json.dumps(payload, ensure_ascii=False)}, files=files,
                                         headers={"X-Test-Scenario": scenario["name"]}, timeout=self.timeout)
            result["status_code"] = response.status_code
            result["response"] = response.text
            try:
                result["response"] = response.json()
            except ValueError:
                pass
            response.raise_for_status()
            body = result["response"]
            if not isinstance(body, dict) or not isinstance(body.get("chat_id"), str) or not isinstance(body.get("sources"), list):
                raise ValueError("Ответ API не содержит chat_id/sources для продолжения диалога")
            image_errors = self.save_charts(body, path)
            if image_errors:
                result["image_errors"] = image_errors
                raise ValueError("Не удалось сохранить графики из ответа")
            if scenario.get("check_saved_artifacts"):
                history_response = self.request("get", f"/agent/chats/{body['chat_id']}/history", timeout=self.timeout)
                history_response.raise_for_status()
                history = history_response.json()["chat_history"]
                saved = next((message for message in history if message["id"] == body["message_id"]), None)
                expected_charts = [{key: value for key, value in chart.items() if key != "image_file"} for chart in body["charts"]]
                if not expected_charts or saved is None or saved.get("charts") != expected_charts:
                    raise ValueError("История не содержит сохранённые артефакты с исходными настройками")
                saved_body = {"charts": saved["charts"]}
                errors = self.save_charts(saved_body, path.with_name(path.stem + "_reopened.json"))
                if errors:
                    raise ValueError("Артефакты из повторно открытой истории недоступны: " + "; ".join(errors))
                result["saved_artifacts_verified"] = True
            next_state = {"chat_id": body["chat_id"], "sources": body["sources"], "aliases": dict(aliases)}
            previous_ids = {source["id"] for source in state["sources"]}
            added = [source for source in body["sources"] if source["id"] not in previous_ids]
            if scenario.get("save_source_as"):
                filename = Path(scenario["file"]).name
                uploaded = [source for source in added if source["name"] == filename]
                if len(uploaded) != 1:
                    raise ValueError("Не удалось однозначно определить загруженный источник")
                next_state["aliases"][scenario["save_source_as"]] = uploaded[0]["id"]
            expected_type = scenario.get("assert_chart_type")
            if expected_type:
                charts = body.get("charts", [])
                if len(charts) != 1 or charts[0].get("chart_type") != expected_type:
                    raise ValueError(f"Ожидался один {expected_type} артефакт")
                if charts[0].get("plotted_points") != scenario["assert_points"]:
                    raise ValueError("Количество точек не совпало с контрольными данными")
                if scenario.get("assert_title") and charts[0].get("title") != scenario["assert_title"]:
                    raise ValueError("Название дашборда не совпало с запрошенным")
                result["evaluation"] = "passed"
            else:
                result["evaluation"] = "manual_review"
        except (ValueError, KeyError, OSError, requests.RequestException) as exc:
            result["error"] = str(exc)
            result["evaluation"] = "skipped" if result.get("skipped") else "request_error"
            next_state = None
        result["duration_seconds"] = round(time.perf_counter() - start, 3)
        path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
        self.results.append(result)
        print(f"{scenario['name']}: {result['evaluation']} ({result['status_code']}); лог: {path}")
        return next_state

    def run(self, cases, dry_run=False):
        if not cases:
            raise ValueError("Набор сценариев пуст")
        self.validate_cases(cases)
        if dry_run:
            for scenario in cases:
                print(json.dumps(scenario, ensure_ascii=False, indent=2))
            print(f"Проверено {len(cases)} сценариев. Запросы не отправлялись.")
            return 0
        self.authenticate()
        state = None
        for scenario in cases:
            followup = scenario.get("use_previous_context", False)
            reason = "Предыдущий шаг диалога не завершился; продолжение не отправлено" if followup and state is None else None
            if not followup:
                state = None
                for index, upload in enumerate(scenario.get("setup_files", [])):
                    setup = {"name": f"{scenario['name']}_upload_{index + 1}", "kind": scenario.get("kind"),
                             "message": "Сохрани приложенный CSV как источник текущего чата. Анализ пока не нужен.",
                             "expected": "CSV зарегистрирован в sources; тот же chat_id используется при следующей загрузке.",
                             "file": upload["file"], "save_source_as": upload["alias"]}
                    state = self.run_scenario(setup, state)
                    if state is None:
                        reason = "Подготовительная загрузка CSV не завершилась; объединение не отправлено"
                        break
            state = self.run_scenario(scenario, state, skip_reason=reason)
        summary = {"scenario_count": len(cases), "request_count": len(self.results),
                   "manual_review": sum(result["evaluation"] == "manual_review" for result in self.results),
                   "passed": sum(result["evaluation"] == "passed" for result in self.results),
                   "errors": sum(result["evaluation"] == "request_error" for result in self.results),
                   "skipped": sum(result["evaluation"] == "skipped" for result in self.results),
                   "note": "HTTP 200 не подтверждает правильность ответа модели. Сопоставьте response.message, sources и графики с expected."}
        (self.logs / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
        print(json.dumps(summary, ensure_ascii=False, indent=2))
        return 1 if summary["errors"] or summary["skipped"] else 0


def run_tool_scenarios(suite="all", dry_run=False, selected_names=None):
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(errors="backslashreplace")
    runner = ToolRunner()
    try:
        cases = select_tool_scenarios(load_scenarios(suite), selected_names)
        return runner.run(cases, dry_run=dry_run)
    except (ValueError, requests.RequestException) as exc:
        print(f"Не удалось запустить сценарии: {exc}")
        return 1
    finally:
        runner.session.close()



if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Сценарии API из scenarios.py с JSON-логами и PNG.")
    parser.add_argument("--suite", choices=("all", "charts", "existing", "tools", "smoke", *TOOL_SUITES), default="smoke")
    parser.add_argument("--prepare", action="store_true", help="Только подготовить CSV из TOOL_DATASETS, без API и модели")
    parser.add_argument("--dry-run", action="store_true", help="Проверить новые сценарии и CSV без запросов")
    parser.add_argument("--scenario", action="append", help="Запустить только указанный новый сценарий; можно повторить")
    args = parser.parse_args()
    if args.prepare:
        try:
            prepare_tool_datasets()
        except (ValueError, OSError, ModuleNotFoundError) as error:
            parser.error(str(error))
        raise SystemExit(0)
    if args.suite in ("tools", "smoke") or args.suite in TOOL_SUITES:
        raise SystemExit(run_tool_scenarios("all" if args.suite == "tools" else args.suite, args.dry_run, args.scenario))
    if args.dry_run or args.scenario:
        parser.error("--dry-run и --scenario поддерживаются набором tools и группами: " + ", ".join(TOOL_SUITES))
    try:
        failures = 0
        if args.suite in ("all", "existing"):
            failures |= run_existing_scenarios()
        if args.suite in ("all", "charts"):
            failures |= run_chart_scenarios()
        if args.suite == "all":
            failures |= run_tool_scenarios("all")
        raise SystemExit(failures)
    except (ValueError, ModuleNotFoundError, AttributeError) as error:
        parser.error(str(error))
