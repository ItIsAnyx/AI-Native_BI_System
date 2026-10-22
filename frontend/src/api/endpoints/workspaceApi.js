// Чаты и проекты пока хранятся только в браузере (заглушки), а ответы нейросети идут с бэкенда.
// Когда появятся эндпоинты для чатов, замените остальные методы вызовами API.
import { publicApi } from "../publicApi";

const id = () => crypto.randomUUID();
// Модель может отвечать долго (на бэкенде REQUEST_TIMEOUT_SECONDS = 300).
const AGENT_TIMEOUT_MS = 5 * 60 * 1000;

export const workspaceApi = {
  async createProject({ name }) {
    return { id: id(), name, open: true };
  },
  async deleteProject(projectId, { deleteChats = false } = {}) {
    return { projectId, deleteChats };
  },
  async createChat({ projectId = null } = {}) {
    return {
      id: id(),
      projectId,
      title: "Новый чат",
      messages: [],
      context: [],
      file: null,
      pending: false,
    };
  },
  async deleteChat(chatId) {
    return { chatId };
  },
  async moveChat(chatId, projectId) {
    return { chatId, projectId };
  },
  // Реальный запрос к нейросети: POST /agent/response (multipart/form-data).
  // Бэкенд не хранит историю: контекст диалога приходит в ответе и отправляется со следующим сообщением.
  async sendMessage({ text, files = [], context = [] }, { signal } = {}) {
    const form = new FormData();
    form.append("payload", JSON.stringify({ message: text, context }));
    if (files[0]) form.append("file", files[0]);
    const data = await publicApi.post("/agent/response", form, {
      signal,
      timeout: AGENT_TIMEOUT_MS,
    });
    return {
      message: { id: id(), role: "assistant", text: data.message },
      context: data.context,
    };
  },
};
