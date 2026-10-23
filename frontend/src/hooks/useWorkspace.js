import { useEffect, useReducer, useRef } from "react";
import { isCanceled, workspaceApi } from "../api/endpoints/workspaceApi";
import { localWorkspaceApi } from "../api/endpoints/localWorkspaceApi";
import {
  initialWorkspace,
  workspaceReducer,
} from "../features/workspace/workspaceReducer";
import { getAgentErrorText } from "../features/workspace/agentErrors";

// demo — режим /demo: без сервера и входа, все данные локальные.
export function useWorkspace(demo = false) {
  const api = demo ? localWorkspaceApi : workspaceApi;
  const [state, dispatch] = useReducer(workspaceReducer, initialWorkspace);
  const requests = useRef(new Map());
  const sending = useRef(false);
  const activeChat = state.chats.find((c) => c.id === state.activeId) ?? null;

  useEffect(() => {
    const pending = requests.current;
    return () => {
      pending.forEach((controller) => controller.abort());
      pending.clear();
    };
  }, []);

  useEffect(() => {
    if (demo) return undefined;
    let cancelled = false;
    dispatch({ type: "chats-loading" });
    workspaceApi
      .listChats()
      .then((chats) => {
        if (!cancelled) dispatch({ type: "chats-loaded", chats });
      })
      .catch(() => {
        if (!cancelled) dispatch({ type: "chats-load-failed" });
      });
    return () => {
      cancelled = true;
    };
  }, [demo]);

  async function createProject(name, chatId = null) {
    const normalized = name.trim().replace(/\s+/g, " ");
    if (!normalized) throw new Error("Введите название проекта.");
    if (normalized.length > 40)
      throw new Error("Название должно быть не длиннее 40 символов.");
    if (
      state.projects.some(
        (p) => p.name.toLowerCase() === normalized.toLowerCase(),
      )
    )
      throw new Error("Проект с таким названием уже существует.");
    const project = await api.createProject({ name: normalized });
    dispatch({ type: "project-created", project });
    if (chatId) await moveChat(chatId, project.id);
    return project;
  }
  async function createChat(projectId = null) {
    const chat = await api.createChat({ projectId });
    dispatch({ type: "chat-created", chat });
    return chat;
  }
  async function deleteChat(id) {
    const chat = state.chats.find((c) => c.id === id);
    await api.deleteChat(id, { serverId: chat?.serverId ?? null });
    requests.current.get(id)?.abort();
    requests.current.delete(id);
    dispatch({ type: "chat-deleted", id });
  }
  async function moveChat(chatId, projectId) {
    await api.moveChat(chatId, projectId);
    dispatch({ type: "chat-moved", chatId, projectId });
  }
  async function deleteProject(id, deleteChats) {
    await api.deleteProject(id, { deleteChats });
    if (deleteChats)
      state.chats
        .filter((c) => c.projectId === id)
        .forEach((c) => {
          requests.current.get(c.id)?.abort();
          requests.current.delete(c.id);
        });
    dispatch({ type: "project-deleted", id, deleteChats });
  }
  function receiveReply(chat, message) {
    const chatId = chat.id;
    const controller = new AbortController();
    requests.current.set(chatId, controller);
    api
      .sendMessage(
        {
          text: message.text,
          file: message.files?.find((f) => f instanceof File) ?? null,
          serverId: chat.serverId ?? null,
        },
        { signal: controller.signal },
      )
      .then(({ message: reply, serverId, sources }) =>
        dispatch({ type: "reply-received", chatId, message: reply, serverId, sources }),
      )
      .catch((error) => {
        if (!isCanceled(error))
          dispatch({
            type: "reply-received",
            chatId,
            message: {
              id: crypto.randomUUID(),
              role: "assistant",
              error: true,
              errorText: getAgentErrorText(error),
            },
          });
      })
      .finally(() => {
        if (requests.current.get(chatId) === controller)
          requests.current.delete(chatId);
      });
  }
  // Переписка чата с сервера подгружается при первом открытии.
  function loadChat(chat) {
    if (demo || !chat?.serverId || chat.loaded || chat.loading) return;
    dispatch({ type: "chat-loading", id: chat.id });
    workspaceApi
      .loadChat(chat.serverId)
      .then(({ messages, sources }) =>
        dispatch({ type: "chat-loaded", id: chat.id, messages, sources }),
      )
      .catch(() => dispatch({ type: "chat-load-failed", id: chat.id }));
  }
  function selectChat(id) {
    dispatch({ type: "chat-selected", id });
    loadChat(state.chats.find((c) => c.id === id));
  }
  function reloadChats() {
    if (demo) return;
    dispatch({ type: "chats-loading" });
    workspaceApi
      .listChats()
      .then((chats) => dispatch({ type: "chats-loaded", chats }))
      .catch(() => dispatch({ type: "chats-load-failed" }));
  }
  async function sendMessage(text, files = []) {
    const value = text.trim();
    // Переписка с сервера ещё не загружена: отправка сейчас перепутала бы историю.
    if (activeChat && (activeChat.loading || !activeChat.loaded)) return false;
    if (
      !value ||
      sending.current ||
      (activeChat && requests.current.has(activeChat.id))
    )
      return false;
    sending.current = true;
    try {
      const chat = activeChat ?? (await createChat());
      const message = {
        id: crypto.randomUUID(),
        role: "user",
        text: value,
        files: [...files],
      };
      dispatch({ type: "message-sent", chatId: chat.id, message });
      receiveReply(chat, message);
      return true;
    } finally {
      sending.current = false;
    }
  }
  function retry() {
    if (
      !activeChat ||
      requests.current.has(activeChat.id) ||
      !activeChat.messages.at(-1)?.error
    )
      return;
    const message = activeChat.messages.findLast((m) => m.role === "user");
    if (!message) return;
    dispatch({ type: "reply-started", chatId: activeChat.id });
    receiveReply(activeChat, message);
  }

  return {
    ...state,
    activeChat,
    createProject,
    createChat,
    deleteChat,
    deleteProject,
    moveChat,
    selectChat,
    loadChat: () => loadChat(activeChat),
    reloadChats,
    toggleProject: (id) => dispatch({ type: "project-toggled", id }),
    sendMessage,
    retry,
  };
}
