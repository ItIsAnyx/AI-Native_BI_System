import { useEffect, useReducer, useRef } from "react";
import { workspaceApi } from "../api/endpoints/workspaceApi";
import {
  initialWorkspace,
  workspaceReducer,
} from "../features/workspace/workspaceReducer";
import {
  getAgentErrorText,
  stripDatasetBlock,
} from "../features/workspace/agentErrors";

export function useWorkspace() {
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
    const project = await workspaceApi.createProject({ name: normalized });
    dispatch({ type: "project-created", project });
    if (chatId) await moveChat(chatId, project.id);
    return project;
  }
  async function createChat(projectId = null) {
    const chat = await workspaceApi.createChat({ projectId });
    dispatch({ type: "chat-created", chat });
    return chat;
  }
  async function deleteChat(id) {
    await workspaceApi.deleteChat(id);
    requests.current.get(id)?.abort();
    requests.current.delete(id);
    dispatch({ type: "chat-deleted", id });
  }
  async function moveChat(chatId, projectId) {
    await workspaceApi.moveChat(chatId, projectId);
    dispatch({ type: "chat-moved", chatId, projectId });
  }
  async function deleteProject(id, deleteChats) {
    await workspaceApi.deleteProject(id, { deleteChats });
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
    // Файл отправляется заново с каждым сообщением, чтобы нейросеть могла вызывать инструменты по данным.
    const file = message.files?.[0] ?? chat.file ?? null;
    const context =
      file && !message.files?.length
        ? stripDatasetBlock(chat.context ?? [])
        : (chat.context ?? []);
    workspaceApi
      .sendMessage(
        { text: message.text, files: file ? [file] : [], context },
        { signal: controller.signal },
      )
      .then(({ message: reply, context: nextContext }) =>
        dispatch({
          type: "reply-received",
          chatId,
          message: reply,
          context: nextContext,
          file,
        }),
      )
      .catch((error) => {
        if (error.name !== "AbortError" && error.name !== "CanceledError")
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
  async function sendMessage(text, files = []) {
    const value = text.trim();
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
    selectChat: (id) => dispatch({ type: "chat-selected", id }),
    toggleProject: (id) => dispatch({ type: "project-toggled", id }),
    sendMessage,
    retry,
  };
}
