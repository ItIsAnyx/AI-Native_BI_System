// Local implementation of the workspace API. Replace these methods with
// privateApi calls when backend endpoints exist; components do not call HTTP.
const id = () => crypto.randomUUID();

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
      pending: false,
    };
  },
  async deleteChat(chatId) {
    return { chatId };
  },
  async moveChat(chatId, projectId) {
    return { chatId, projectId };
  },
  sendMessage({ text }, { signal, retry = false } = {}) {
    return new Promise((resolve, reject) => {
      if (signal?.aborted)
        return reject(new DOMException("Aborted", "AbortError"));
      const abort = () => {
        clearTimeout(timer);
        reject(new DOMException("Aborted", "AbortError"));
      };
      const timer = setTimeout(() => {
        signal?.removeEventListener("abort", abort);
        if (!retry && /\/error/i.test(text))
          return reject(new Error("Демонстрационная ошибка ответа"));
        resolve({ id: id(), role: "assistant", source: "demo" });
      }, 1100);
      signal?.addEventListener("abort", abort, { once: true });
    });
  },
};
