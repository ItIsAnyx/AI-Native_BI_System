# AI-Native BI System

Анализ CSV через чат с локальной моделью: расчёты, графики и сохранённые дашборды.

## Что установить

- [Docker Desktop](https://www.docker.com/products/docker-desktop/) — запустить перед сборкой.
- [Ollama для Windows](https://ollama.com/download/windows).

Команды ниже выполняются в PowerShell. Приложение и PostgreSQL запускаются в Docker, модель — через Ollama на компьютере.

## 1. Запустить Ollama

Если Ollama уже работает в трее, завершите её. В отдельном PowerShell выполните и оставьте окно открытым:

```powershell
$env:OLLAMA_HOST = "0.0.0.0:11434"
ollama serve
```

Этот адрес позволяет приложению в Docker обращаться к Ollama ([настройка сервера](https://docs.ollama.com/faq#how-do-i-configure-ollama-server)).

## 2. Подготовить модель

Скачайте [Qwen3.8-4B-Q4_K_M.gguf](https://huggingface.co/empero-ai/Qwen3.8-4B-Distill-GGUF/blob/main/Qwen3.8-4B-Q4_K_M.gguf) и положите в `backend/models`.
Modelfile и токенизатор уже находятся в репозитории.

Во втором PowerShell выполните:

```powershell
Set-Location D:\AI-Native_BI_System
ollama create qwen38-4b-local -f .\backend\models\Modelfile
ollama list
```

В списке должна появиться `qwen38-4b-local`. Импорт нужен один раз.

## 3. Подготовить настройки

Из корня проекта создайте отсутствующие файлы настроек:

```powershell
if (!(Test-Path .env)) { Copy-Item .env.example .env }
if (!(Test-Path backend/.env)) { Copy-Item backend/.env.example backend/.env }
```

Значения `DB_USERNAME`, `DB_PASSWORD`, `DB_DATABASE` должны совпадать в обоих файлах.
В `backend/.env` проверьте:

```dotenv
MODEL_NAME=qwen38-4b-local
TOKENIZER_PATH=models/tokenizer
MAX_CONTEXT_TOKENS=40960
```

Для первого локального запуска остальные значения можно оставить из примеров.
Адреса PostgreSQL, Ollama и интерфейса внутри Docker уже заданы в `docker-compose.yaml`.

## 4. Запустить приложение

Порты **3000, 8080 и 5432** должны быть свободны. Если ранее запускали backend отдельно на 8080, остановите его.

```powershell
docker compose up -d --build
docker compose ps
```

После запуска откройте **http://localhost:3000**, зарегистрируйтесь, создайте чат и загрузите CSV.
Например, отправьте: «Опиши данные» или «Создай дашборд по этим данным».
На CPU ответ модели может занимать несколько минут.

## Остановка и диагностика

```powershell
docker compose logs -f backend   # Логи сервера; Ctrl+C завершает просмотр
docker compose down              # Остановка с сохранением данных
```

Не добавляйте `-v` к остановке, если нужно сохранить пользователей, историю и файлы.
При ошибке связи с моделью проверьте `ollama list` и окно с `ollama serve`.

Документация: [архитектура и стек](Architecture.md), [сценарии и критерии](Сriteria.md).
