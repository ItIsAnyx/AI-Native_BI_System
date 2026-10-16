# Aster — React frontend

React frontend for Aster. Source code is organized by responsibility; see the structure below.

## Run

```sh
npm ci
npm run dev
```

Open http://localhost:5174. The dev proxy forwards `/api` to
http://localhost:8080. Start the existing backend separately with its configured
PostgreSQL database. To use another API origin, set `VITE_API_URL` before starting
Vite. For production builds the variable must be available at build time.

```sh
npm run build
npm run lint
```

## Authentication

Login, registration, `/me`, token refresh and logout use the existing backend
endpoints and HttpOnly cookies through `publicApi` and `privateApi`.
The auth store contains only the user, initialization flag and basic actions.
`/` is protected; `/login` and `/register` are public. `/demo` is a separate local
preview and never marks a visitor as authenticated. Password recovery is not
implemented by the backend and the UI says so.

## Структура приложения

```text
src/
  pages/                    Страницы маршрутов и сборка интерфейса
  layouts/                  Общие оболочки страниц
  components/
    common/                 Бренд и иконки
    ui/                     Кнопка, поле, модальное окно, уведомление
    workspace/
      sidebar/              Навигация, проект со списком чатов, аккаунт
      dialogs/              Создание/удаление проекта, удаление/перенос чата
      Sidebar.jsx           Оболочка боковой панели и поиск
      WorkspaceHeader.jsx   Заголовок и открытие мобильного меню
      WorkspaceTabs.jsx     Переключение вкладок с клавиатуры
      WorkspacePanels.jsx   Содержимое вкладок
      Chat*.jsx             Переписка, сообщение и ввод сообщения
  hooks/                    Логика React и жизненный цикл
  features/
    auth/                   Валидация форм, ошибки API, безопасный возврат
    workspace/              Reducer состояния проектов и чатов
  api/                      HTTP-клиенты и методы API
  store/                    Общее состояние авторизации
  types/                    Типы авторизации
  styles/                   Базовые стили и стили разделов
```

`App.jsx` задаёт маршруты и инициализацию авторизации. Страницы собирают
компоненты и связывают их действия. Компоненты не обращаются к HTTP напрямую:
`useWorkspace` управляет действиями и отменой запросов, `workspaceReducer` —
изменением данных, `workspaceApi` — доступом к данным.

`WorkspaceDialogs` только выбирает диалог. Каждый диалог хранит собственные
поля, а `useDialogAction` обрабатывает ожидание, ошибки и успешное закрытие.
`useDrawerFocus` отвечает за клавиатуру и возврат фокуса мобильного меню,
`useToast` — за время показа уведомлений.

Вход и регистрация используют общий `useAuthForm`. Правила полей находятся
в `features/auth/loginForm.js` и `registerForm.js`; разбор серверных ошибок
и проверка адреса возврата также вынесены в отдельные функции.

Где менять код:

- Новый раздел рабочего пространства: `WorkspaceTabs` и `WorkspacePanels`.
- Вид проекта или аккаунта: `components/workspace/sidebar/`.
- Новый диалог: `components/workspace/dialogs/` и `WorkspaceDialogs`.
- Поведение чатов: `useWorkspace` и `workspaceReducer`.
- Подключение сервера: `api/endpoints/`, без изменений компонентов.

## Connecting additional backend endpoints

`src/api/endpoints/workspaceApi.js` is the replacement boundary for workspace
operations. The current implementation is local and asynchronous. Projects and
chats live in React state and reset on reload; replies are explicitly marked as
sample responses. Dashboard and Data sources remain the original placeholders.

Replace method bodies with `privateApi` calls while keeping these contracts:

| Method | Input | Result |
| --- | --- | --- |
| createProject | `{ name }` | `{ id, name, open }` |
| deleteProject | `projectId, { deleteChats }` | completion |
| createChat | `{ projectId }` | `{ id, projectId, title, messages, pending }` |
| deleteChat | `chatId` | completion |
| moveChat | `chatId, projectId` | completion |
| sendMessage | `{ chatId, text, files }`, `{ signal, retry }` | assistant message |

IDs are strings. The composer passes actual `File` objects (up to five) to the
workspace API boundary; it does not currently upload or parse them. Use
`FormData` or a separate upload endpoint when the backend supports attachments.
Pass `signal` through to Axios for cancellation when a chat is removed or the
workspace unmounts. Return `{ id, role: "assistant", text }` for real replies; `ChatMessage` already
renders their text. Only messages with `source: "demo"` use the sample block. A backend list endpoint will
also need to populate initial workspace state for persistent history.

## Docker

```sh
docker build -t aster-frontend --build-arg VITE_API_URL=http://localhost:8080 .
docker run --rm -p 3000:3000 aster-frontend
```

Use a browser-reachable API origin and configure the backend CORS origin to
match the frontend address. The container serves `dist` with SPA fallback.
