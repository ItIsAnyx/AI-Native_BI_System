export const initialWorkspace = { projects: [], chats: [], activeId: null };

export function workspaceReducer(state, action) {
  switch (action.type) {
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
                context: action.context ?? c.context,
                file: action.file !== undefined ? action.file : c.file,
                messages: [...c.messages, action.message],
              }
            : c,
        ),
      };
    default:
      return state;
  }
}
