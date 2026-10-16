import ChatThread from "./ChatThread";
import ChatComposer from "./ChatComposer";
import WorkspacePlaceholder from "./WorkspacePlaceholder";

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
        />
        <ChatComposer
          key={workspace.activeId ?? "empty"}
          pending={workspace.activeChat?.pending ?? false}
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
        <WorkspacePlaceholder icon="grid" title="Dashboard">
          Раздел появится позже. Здесь будут сводки по проектам и активности.
        </WorkspacePlaceholder>
      </section>
      <section
        role="tabpanel"
        id="panel-data"
        aria-labelledby="tab-data"
        className="panel"
        hidden={tab !== "data"}
      >
        <WorkspacePlaceholder icon="db" title="Data sources">
          Раздел появится позже. Здесь можно будет подключать документы и
          сервисы.
        </WorkspacePlaceholder>
      </section>
    </div>
  );
}
