import ChatThread from "./ChatThread";
import ChatComposer from "./ChatComposer";
import DashboardLibrary from "./DashboardLibrary";
import DatabaseConnector from "./DatabaseConnector";
import SourcesPanel from "./SourcesPanel";

export default function WorkspacePanels({ tab, workspace, onSend, notify }) {
  return (
    <div className="panels">
      <section
        role="tabpanel"
        id="panel-chat"
        aria-labelledby="tab-chat"
        className="panel panel-chat"
        hidden={tab !== "chat"}
      >
        <ChatThread
          chat={workspace.activeChat}
          onSend={onSend}
          onRetry={workspace.retry}
          onReload={workspace.loadChat}
        />
        <ChatComposer
          stopping={workspace.activeChat?.stopping ?? false}
          onStop={workspace.activeChat?.pending ? () => workspace.stopRequest(workspace.activeId) : undefined}
          key={workspace.activeId ?? "empty"}
          pending={
            (workspace.activeChat?.pending || workspace.activeChat?.loading) ??
            false
          }
          onSend={onSend}
          notify={notify}
        />
      </section>
      <section
        role="tabpanel"
        id="panel-dash"
        aria-labelledby="tab-dash"
        className="panel"
        hidden={tab !== "dash"}
      >
        {workspace.demo ? <p>Войдите в аккаунт, чтобы создавать и сохранять дашборды.</p> :
          <DashboardLibrary visible={tab === "dash"} chats={workspace.chats} />}
      </section>
      <section
        role="tabpanel"
        id="panel-data"
        aria-labelledby="tab-data"
        className="panel"
        hidden={tab !== "data"}
      >
        <SourcesPanel chat={workspace.activeChat} />
        {tab === "data" && !workspace.demo && <DatabaseConnector onConnect={workspace.connectSource} />}
      </section>
    </div>
  );
}
