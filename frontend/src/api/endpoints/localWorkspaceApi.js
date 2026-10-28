// Локальные (не серверные) операции: проекты и черновики чатов.
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
};
