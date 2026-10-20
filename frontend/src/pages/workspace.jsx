import { useCallback, useEffect, useRef, useState } from "react";
import { useTransitionNavigate } from "../hooks/useTransitionNavigate";
import { useAuth } from "../hooks/useAuth";
import { useWorkspace } from "../hooks/useWorkspace";
import { useToast } from "../hooks/useToast";
import Toast from "../components/ui/Toast";
import WorkspaceHeader from "../components/workspace/WorkspaceHeader";
import WorkspacePanels from "../components/workspace/WorkspacePanels";
import Sidebar from "../components/workspace/Sidebar";
import WorkspaceTabs from "../components/workspace/WorkspaceTabs";
import WorkspaceDialogs from "../components/workspace/WorkspaceDialogs";

const demoUser = { id: "demo", login: "Анна Крылова", email: "demo@aster.app" };

export default function Workspace({ demo = false }) {
  const { user, logout } = useAuth();
  const navigate = useTransitionNavigate();
  const workspace = useWorkspace();
  const [query, setQuery] = useState("");
  const [drawer, setDrawer] = useState(false);
  const [tab, setTab] = useState("chat");
  const [modal, setModal] = useState(null);
  const { toast, notify, dismissToast } = useToast();
  const [loggingOut, setLoggingOut] = useState(false);
  const main = useRef(null);
  const closeDrawer = useCallback(() => setDrawer(false), []);
  const closeModal = useCallback(() => setModal(null), []);
  useEffect(() => {
    const screen = window.matchMedia("(min-width:861px)");
    const close = () => setDrawer(false);
    screen.addEventListener("change", close);
    return () => screen.removeEventListener("change", close);
  }, []);
  const project = workspace.projects.find(
    (p) => p.id === workspace.activeChat?.projectId,
  );
  async function newChat(projectId = null) {
    try {
      await workspace.createChat(projectId);
      setQuery("");
      setTab("chat");
      closeDrawer();
    } catch {
      notify("Не удалось создать чат. Попробуйте ещё раз.");
    }
  }
  function selectChat(id) {
    workspace.selectChat(id);
    setTab("chat");
    closeDrawer();
    main.current?.focus();
  }
  async function send(text, files = []) {
    try {
      return await workspace.sendMessage(text, files);
    } catch {
      notify("Не удалось отправить сообщение. Попробуйте ещё раз.");
      return false;
    }
  }
  async function signOut() {
    if (loggingOut) return;
    setLoggingOut(true);
    try {
      if (!demo) await logout();
      navigate("/login", { replace: true });
    } catch {
      notify("Не удалось выйти. Проверьте подключение и повторите попытку.");
    } finally {
      setLoggingOut(false);
    }
  }
  return (
    <div className="app">
      <Sidebar
        workspace={workspace}
        user={demo ? demoUser : user}
        demo={demo}
        query={query}
        onQuery={setQuery}
        open={drawer}
        onClose={closeDrawer}
        onNewChat={newChat}
        onSelect={selectChat}
        onDialog={setModal}
        onLogout={signOut}
        loggingOut={loggingOut}
      />
      <main
        ref={main}
        inert={drawer}
        className="main"
        id="main-anchor"
        tabIndex={-1}
      >
        <WorkspaceHeader
          title={workspace.activeChat?.title}
          projectName={project?.name}
          demo={demo}
          drawer={drawer}
          onOpenMenu={() => setDrawer(true)}
        />
        <WorkspaceTabs value={tab} onChange={setTab} />
        <WorkspacePanels
          tab={tab}
          workspace={workspace}
          onSend={send}
          notify={notify}
        />
      </main>
      {modal && (
        <WorkspaceDialogs
          key={`${modal.type}-${modal.id ?? modal.chatId ?? "new"}`}
          modal={modal}
          workspace={workspace}
          onClose={closeModal}
          onDialog={setModal}
          notify={notify}
          onProjectCreated={() => setQuery("")}
        />
      )}
      <Toast message={toast} onDismiss={dismissToast} />
    </div>
  );
}
