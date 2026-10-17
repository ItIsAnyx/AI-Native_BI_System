# Локальный чат через Ollama

Приложение обращается к локальной Ollama через OpenAI-совместимый API.
Ollama загружает веса и выполняет генерацию; backend обрабатывает контекст и CSV.
Установка Python-пакета `ollama` не нужна. Transformers и PyTorch для этого пути не нужны.

## Установка Ollama на Windows

1. Скачайте установщик с https://ollama.com/download/windows и установите Ollama.
2. Откройте новый PowerShell и выполните `ollama --version`.
3. Проверьте сервер: `Invoke-RestMethod http://127.0.0.1:11434/api/tags`.

Windows-приложение Ollama обычно запускает сервер в фоне. Если сервер не запущен,
откройте Ollama через меню «Пуск» или выполните в отдельном терминале:

```powershell
ollama serve
```

При ручном запуске оставьте этот терминал открытым. Если порт 11434 уже занят Ollama,
не запускайте второй экземпляр. Облачная учётная запись для локального GGUF не нужна.

Официальная инструкция: https://docs.ollama.com/windows

## Импорт локального GGUF

Скачайте выбранный GGUF со страницы:
https://huggingface.co/empero-ai/Qwen3.8-4B-Distill-GGUF/tree/main

Для первого запуска можно взять `Qwen3.8-4B-Q4_K_M.gguf` (около 2.8 GB весов).
Размер файла не равен общему потреблению RAM/VRAM: контекст требует дополнительной памяти.
Автор указывает необходимость свежего движка с поддержкой архитектуры Qwen3.5.

Поместите файл в `backend/models`. Рядом создайте файл `Modelfile` без расширения:

```text
FROM ./Qwen3.8-4B-Q4_K_M.gguf
PARAMETER num_ctx 8192
PARAMETER temperature 0.6
PARAMETER top_p 0.95
PARAMETER top_k 20
```

`FROM` задаёт путь к GGUF относительно Modelfile. `num_ctx` задаёт окно в токенах;
оно влияет на потребление памяти. Остальные параметры задают настройки генерации.
Шаблон чата у выбранной модели встроен в GGUF; вручную писать TEMPLATE сначала не нужно.

Из папки проекта выполните:

```powershell
Set-Location D:\GitWorks\AI-Native_BI_System\backend\models
ollama create qwen38-local -f .\Modelfile
ollama list
ollama run qwen38-local
```

`qwen38-local` — выбранное вами имя модели в Ollama. В списке оно может отображаться
как `qwen38-local:latest`; это имя с тегом по умолчанию. Спросите модель что-нибудь.
Для выхода из интерактивного диалога используйте `/bye`.

Ollama импортирует модель в своё хранилище, а не просматривает backend/models
перед каждым запросом. Папка проекта хранит исходные файлы; нужно учитывать место
и для хранилища Ollama. Для другой модели повторите импорт под другим именем.

Официальная инструкция импорта: https://docs.ollama.com/import
Параметры Modelfile: https://docs.ollama.com/modelfile

## Проверка API отдельно от приложения

В PowerShell:

```powershell
$body = @{
    model = 'qwen38-local'
    messages = @(@{ role = 'user'; content = 'Reply with a short greeting.' })
    stream = $false
} | ConvertTo-Json -Depth 10

$result = Invoke-RestMethod -Method Post `
    -Uri 'http://127.0.0.1:11434/v1/chat/completions' `
    -ContentType 'application/json; charset=utf-8' `
    -Body $body

$result.choices[0].message.content
```

Первый запрос может быть медленным из-за загрузки весов. `ollama ps` показывает
загруженные модели. `ollama stop qwen38-local` выгружает модель; сервер продолжает работать.

Выбранная модель обучена рассуждать и может выдавать блоки `<think>`. Проверьте,
отделяет ли установленная версия Ollama рассуждения от content. В приложении пока
нет дополнительного удаления таких блоков; оно возвращает message.content как есть.

Совместимость API: https://docs.ollama.com/api/openai-compatibility

## Подключение backend

Из папки backend:

```powershell
Set-Location D:\GitWorks\AI-Native_BI_System\backend
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

Если `.env` ещё нет, скопируйте `.env.example` в `.env`. Существующий файл не затирайте:
обновите только нужные настройки. Укажите:

```dotenv
BACKEND_KEY=change-this-local-key
OLLAMA_BASE_URL=http://127.0.0.1:11434/v1
MODEL_NAME=qwen38-local
REQUEST_TIMEOUT_SECONDS=300
MAX_REQUEST_LENGTH=8000
MAX_CONTEXT_LENGTH=12000
MAX_FILE_SIZE_MB=10
MAX_FILE_ROWS=100000
```

Замените BACKEND_KEY своим значением. Это ключ вашего эндпоинта, не ключ Ollama.
MODEL_NAME — имя из `ollama list`, а не путь к файлу и не имя репозитория Hugging Face.
Старые MODEL_PATH и MAX_NEW_TOKENS больше не используются.

MAX_CONTEXT_LENGTH считается в символах и запускает пересказ; num_ctx у Ollama
считается в токенах. Между ними нет точного постоянного коэффициента. Здесь 12000
символов — начальный порог, который нужно проверить на ваших данных. Пересказ,
последний запрос, данные файлов и ответ должны помещаться в окно модели.

Запустите приложение:

```powershell
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Ollama должна продолжать работать в фоне. Backend сам её не запускает и веса не скачивает.
При смене MODEL_NAME или других настроек перезапустите backend.

## Проверка приложения

Откройте http://127.0.0.1:8000/docs и выберите POST /agent/response.
Нажмите Try it out, укажите BACKEND_KEY из `.env`, а в payload вставьте:

```json
{
  "message": "Привет! Ответь одним предложением.",
  "context": []
}
```

Поле file необязательное. Для вопроса о CSV выберите файл и измените message.
Ответ содержит `message` и `context`. В следующий запрос передайте новый message
и context из предыдущего ответа. Это активный контекст, не полная история чата.
Историю сохраняет основной backend отдельно.

CSV читается в tools/dataset.py: определяются разделитель и типы pandas,
убираются пробелы, собирается статистика и пять примеров строк. Информация
добавляется к первому системному сообщению и сохраняется при пересказе.
Если контекст длинный, промежуточные сообщения заменяются одним пересказом.
Первое системное сообщение и последний запрос пользователя сохраняются.

GET /api/health проверяет только приложение; доступность модели проверяет реальный запрос.

## Ошибки

- 403: неверный BACKEND_KEY.
- 422: неверный payload или пустое сообщение.
- 503 с Cannot connect: Ollama не запущена или указан неверный OLLAMA_BASE_URL.
- 503 с Model not found: MODEL_NAME не совпадает с именем импортированной модели.
- 504: превышен REQUEST_TIMEOUT_SECONDS; проверьте модель отдельно и при необходимости увеличьте таймаут.
- 502: Ollama отклонила запрос или вернула пустой ответ; проверьте её логи и прямой запрос.
- Ошибка архитектуры при импорте/загрузке: обновите Ollama и проверьте поддержку модели.
- Нехватка памяти: уменьшите num_ctx в Modelfile и повторите ollama create либо используйте меньшую модель.

Логи Ollama на Windows находятся в `%LOCALAPPDATA%\Ollama`, в частности server.log.
Установка зависимостей backend не устанавливает саму Ollama.

## Смена модели

Импортируйте другой GGUF под новым именем, проверьте `ollama run`, измените MODEL_NAME
и перезапустите backend. Выпадающий список моделей и загрузка через UI пока не реализованы.
