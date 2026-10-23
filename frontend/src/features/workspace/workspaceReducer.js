export const initialWorkspace = {
  projects: [],
  chats: [],
  activeId: null,
  chatsLoading: false,
  chatsError: false,
};

const patchChat = (state, id, patch) => ({
  ...state,
  chats: state.chats.map((c) => (c.id === id ? { ...c, ...patch } : c)),
});

export function workspaceReducer(state, action) {
  switch (action.type) {
    case "chats-loading":
      return { ...state, chatsLoading: true, chatsError: false };
    case "chats-load-failed":
      return { ...state, chatsLoading: false, chatsError: true };
    case "chats-loaded": {
      // Локальные черновики (ещё не отправленные на сервер) остаются сверху.
      const known = new Set(state.chats.map((c) => c.serverId).filter(Boolean));
      return {
        ...state,
        chatsLoading: false,
        chatsError: false,
        chats: [
          ...state.chats,
          ...action.chats.filter((c) => !known.has(c.serverId)),
        ],
      };
    }
    case "chat-loading":
      return patchChat(state, action.id, { loading: true, loadError: false });
    case "chat-load-failed":
      return patchChat(state, action.id, { loading: false, loadError: true });
    case "chat-loaded":
      return patchChat(state, action.id, {
        loading: false,
        loadError: false,
        loaded: true,
        messages: action.messages,
        sources: action.sources,
      });
    case "project-created":
      return { ...state, projects: [...state.projects, action.project] };
    case "project-toggled":
      return {
        ...state,
        projects: state.projects.map((p) =>
          p.id === action.id ? { ...p, open: !p.open } : p,
        ),
      };
    case "chat-created":
      return {
        ...state,
        chats: [action.chat, ...state.chats],
        activeId: action.chat.id,
        projects: state.projects.map((p) =>
          p.id === action.chat.projectId ? { ...p, open: true } : p,
        ),
      };
    case "chat-selected":
      return { ...state, activeId: action.id };
    case "chat-deleted": {
      const chats = state.chats.filter((c) => c.id !== action.id);
      return {
        ...state,
        chats,
        activeId:
          state.activeId === action.id
            ? (chats[0]?.id ?? null)
            : state.activeId,
      };
    }
    case "chat-moved":
      return {
        ...state,
        chats: state.chats.map((c) =>
          c.id === action.chatId ? { ...c, projectId: action.projectId } : c,
        ),
        projects: state.projects.map((p) =>
          p.id === action.projectId ? { ...p, open: true } : p,
        ),
      };
    case "project-deleted": {
      const chats = action.deleteChats
        ? state.chats.filter((c) => c.projectId !== action.id)
        : state.chats.map((c) =>
            c.projectId === action.id ? { ...c, projectId: null } : c,
          );
      return {
        ...state,
        projects: state.projects.filter((p) => p.id !== action.id),
        chats,
        activeId: chats.some((c) => c.id === state.activeId)
          ? state.activeId
          : (chats[0]?.id ?? null),
      };
    }
    case "message-sent":
      return {
        ...state,
        chats: state.chats.map((c) =>
          c.id === action.chatId
            ? {
                ...c,
                pending: true,
                title: c.messages.length
                  ? c.title
                  : action.message.text.slice(0, 38) +
                    (action.message.text.length > 38 ? "…" : ""),
                messages: [...c.messages, action.message],
              }
            : c,
        ),
      };
    case "reply-started":
      return {
        ...state,
        chats: state.chats.map((c) =>
          c.id === action.chatId
            ? {
                ...c,
                pending: true,
                messages: c.messages.at(-1)?.error
                  ? c.messages.slice(0, -1)
                  : c.messages,
              }
            : c,
        ),
      };
    case "reply-received":
      return {
        ...state,
        chats: state.chats.map((c) =>
          c.id === action.chatId
            ? {
                ...c,
                pending: false,
                serverId: action.serverId ?? c.serverId,
                sources: action.sources ?? c.sources,
                messages: [...c.messages, action.message],
              }
            : c,
        ),
      };
    default:
      return state;
  }
}
