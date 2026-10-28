import axios from "axios";
import { privateApi } from "../privateApi";
import { localWorkspaceApi } from "./localWorkspaceApi";

const id = () => crypto.randomUUID();
// Один запрос может содержать несколько вызовов модели (до MAX_TOOL_CALLS),
// каждый ограничен REQUEST_TIMEOUT_SECONDS (в .env.example — 600 с).
// По умолчанию ждём 15 минут; задаётся VITE_AGENT_TIMEOUT_SEC.
const AGENT_TIMEOUT_MS =
  (Number(import.meta.env.VITE_AGENT_TIMEOUT_SEC) || 15 * 60) * 1000;
const API_BASE = (import.meta.env.VITE_API_URL || "").replace(/\/$/, "");

// Адрес файла с сервера (графики, CSV). Относительный путь работает через прокси Vite.
export function assetUrl(path) {
  return /^https?:\/\//.test(path) ? path : `${API_BASE}${path}`;
}

function toChat(row) {
  return {
    id: row.id,
    serverId: row.id,
    projectId: null,
    title: row.title,
    messages: [],
    sources: [],
    loaded: false,
    loading: false,
    loadError: false,
    pending: false,
  };
}

// История с сервера: {id, role, content, source_ids, charts} → сообщения интерфейса.
function toMessages(history, sources) {
  const names = new Map(sources.map((s) => [s.id, s.name]));
  return history.map((m) => {
    if (m.role === "user")
      return {
        id: m.id,
        role: "user",
        text: m.content,
        files: (m.source_ids ?? [])
          .filter((sourceId) => names.has(sourceId))
          .map((sourceId) => ({ name: names.get(sourceId) })),
      };
    return {
      id: m.id,
      role: "assistant",
      text: m.content,
      charts: m.charts ?? [],
    };
  });
}

export const workspaceApi = {
  // Проекты и перенос чатов пока только локальные: на бэкенде их нет.
  ...localWorkspaceApi,

  async listChats() {
    const rows = await privateApi.get("/agent/chats");
    return rows.map(toChat);
  },

  // После обрыва связи: ответ мог сохраниться. Ищем его в истории (для нового
  // чата сначала находим его в списке по заголовку = первые 80 символов запроса).
  async findReply({ serverId, text, knownIds = [], expected }) {
    let id = serverId;
    if (!id) {
      const wanted = text.trim().slice(0, 80);
      const known = new Set(knownIds);
      const rows = await privateApi.get("/agent/chats");
      id = rows.find((r) => !known.has(r.id) && r.title.trim() === wanted)?.id;
      if (!id) return null;
    }
    const loaded = await workspaceApi.loadChat(id);
    const { messages } = loaded;
    const last = messages.at(-1);
    const found =
      messages.length >= expected + 1 &&
      last?.role === "assistant" &&
      messages.at(-2)?.text?.trim() === text.trim();
    return found ? { serverId: id, ...loaded } : null;
  },

  async loadChat(serverId) {
    const [history, sourcesData] = await Promise.all([
      privateApi.get(`/agent/chats/${serverId}/history`),
      privateApi.get(`/agent/chats/${serverId}/sources`),
    ]);
    return {
      messages: toMessages(history.chat_history, sourcesData.sources),
      sources: sourcesData.sources,
    };
  },

  // Локальный чат без serverId на сервере не существует: удаляем только в браузере.
  async deleteChat(chatId, { serverId = null } = {}) {
    if (!serverId) return { chatId };
    try {
      await privateApi.delete(`/agent/chats/${serverId}`);
    } catch (error) {
      if ([404, 405].includes(error.response?.status))
        throw new Error("Сервер пока не поддерживает удаление чатов.", { cause: error });
      throw error;
    }
    return { chatId };
  },

  // POST /agent/response (multipart/form-data). Без serverId сервер сам создаёт чат.
  async sendMessage(
    { text, file = null, serverId = null },
    { signal, onUploadProgress } = {},
  ) {
    const form = new FormData();
    form.append(
      "payload",
      JSON.stringify({ message: text, chat_id: serverId }),
    );
    if (file) form.append("file", file);
    const data = await privateApi.post("/agent/response", form, {
      signal,
      timeout: AGENT_TIMEOUT_MS,
      onUploadProgress: file ? onUploadProgress : undefined,
    });
    return {
      message: {
        id: data.message_id ?? id(),
        role: "assistant",
        text: data.message,
        charts: data.charts ?? [],
      },
      serverId: data.chat_id,
      sources: data.sources ?? [],
    };
  },
};

export const isCanceled = (error) =>
  error?.name === "AbortError" || axios.isCancel(error);
