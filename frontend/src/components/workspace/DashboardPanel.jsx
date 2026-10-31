import { useState } from "react";
import "../../styles/dashboard-scope.css";
import { collectCharts, isDashboard } from "../../features/workspace/charts";
import DashboardCard from "./DashboardCard";
import DashboardLibrary from "./DashboardLibrary";
import WorkspacePlaceholder from "./WorkspacePlaceholder";

const SCOPES = [
  { id: "chat", label: "Этот чат" },
  { id: "all", label: "Все чаты" },
];

function Section({ id, title, items, onOpenMessage }) {
  if (!items.length) return null;
  return (
    <section aria-labelledby={id}>
      <h2 id={id}>{title}</h2>
      <ul className="dash-grid">
        {items.map(({ chart, messageId }) => (
          <DashboardCard
            key={chart.id}
            chart={chart}
            actions={
              <button
                type="button"
                className="btn btn-secondary btn-sm"
                onClick={() => onOpenMessage(messageId)}
              >
                Показать в чате
              </button>
            }
          />
        ))}
      </ul>
    </section>
  );
}

// Графики и дашборды текущего чата (из его истории) либо дашборды всех чатов.
function ChatCharts({ chat, onOpenMessage }) {
  if (chat?.loading)
    return (
      <p className="muted center" role="status">
        Загрузка переписки…
      </p>
    );
  const items = collectCharts(chat?.messages).reverse();
  if (!items.length)
    return (
      <WorkspacePlaceholder icon="grid" title="Dashboard">
        В этом чате пока нет графиков. Загрузите CSV и попросите построить
        дашборд — он сохранится здесь.
      </WorkspacePlaceholder>
    );
  return (
    <>
      <Section
        id="dash-h"
        title="Дашборды"
        items={items.filter((i) => isDashboard(i.chart))}
        onOpenMessage={onOpenMessage}
      />
      <Section
        id="charts-h"
        title="Графики"
        items={items.filter((i) => !isDashboard(i.chart))}
        onOpenMessage={onOpenMessage}
      />
    </>
  );
}

export default function DashboardPanel({
  chat,
  chats,
  visible,
  onOpenMessage,
  onOpenChat,
}) {
  const [scope, setScope] = useState("chat");
  return (
    <div className="dash">
      <div className="dash-scope" role="group" aria-label="Какие дашборды показывать">
        {SCOPES.map((item) => (
          <button
            key={item.id}
            type="button"
            aria-pressed={scope === item.id}
            onClick={() => setScope(item.id)}
          >
            {item.label}
          </button>
        ))}
      </div>
      {scope === "chat" ? (
        <ChatCharts chat={chat} onOpenMessage={onOpenMessage} />
      ) : (
        <DashboardLibrary visible={visible} chats={chats} onOpenChat={onOpenChat} />
      )}
    </div>
  );
}
