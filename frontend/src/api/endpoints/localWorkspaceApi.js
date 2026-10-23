// Локальные (не серверные) операции: проекты, а также режим /demo целиком.
// Проекты на бэкенде пока не поддерживаются, поэтому живут только в браузере.
const id = () => crypto.randomUUID();

export const localWorkspaceApi = {
  async createProject({ name }) {
    return { id: id(), name, open: true };
  },
  async deleteProject(projectId, { deleteChats = false } = {}) {
    return { projectId, deleteChats };
  },
  // Чат создаётся локально; на сервере он появляется вместе с первым сообщением.
  async createChat({ projectId = null } = {}) {
    return {
      id: id(),
      serverId: null,
      projectId,
      title: "Новый чат",
      messages: [],
      sources: [],
      loaded: true,
      loading: false,
      loadError: false,
      pending: false,
    };
  },
  async deleteChat(chatId) {
    return { chatId };
  },
  async moveChat(chatId, projectId) {
    return { chatId, projectId };
  },
  // Демонстрационный ответ (только для /demo, без сервера).
  sendMessage({ text }, { signal } = {}) {
    return new Promise((resolve, reject) => {
      if (signal?.aborted)
        return reject(new DOMException("Aborted", "AbortError"));
      const abort = () => {
        clearTimeout(timer);
        reject(new DOMException("Aborted", "AbortError"));
      };
      const timer = setTimeout(() => {
        signal?.removeEventListener("abort", abort);
        if (/\/error/i.test(text))
          return reject(new Error("Демонстрационная ошибка ответа"));
        resolve({
          message: { id: id(), role: "assistant", source: "demo" },
          serverId: null,
          sources: [],
        });
      }, 1100);
      signal?.addEventListener("abort", abort, { once: true });
    });
  },
};
