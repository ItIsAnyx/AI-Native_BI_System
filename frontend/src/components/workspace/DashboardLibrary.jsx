import { useEffect, useState } from "react";
import Icon from "../common/Icon";
import { assetUrl, workspaceApi } from "../../api/endpoints/workspaceApi";
import DashboardCard from "./DashboardCard";

// Сохранённые дашборды из всех чатов пользователя (GET /agent/dashboards).
export default function DashboardLibrary({ visible, chats, onOpenChat }) {
  const [items, setItems] = useState([]);
  const [status, setStatus] = useState("loading");
  const [revision, setRevision] = useState(0);
  useEffect(() => {
    if (!visible) return undefined;
    let cancelled = false;
    workspaceApi
      .listDashboards()
      .then((rows) => {
        if (cancelled) return;
        setItems(rows);
        setStatus("ready");
      })
      .catch(() => {
        if (!cancelled) setStatus("error");
      });
    return () => {
      cancelled = true;
    };
  }, [visible, chats, revision]);
  function refresh() {
    setStatus("loading");
    setRevision((r) => r + 1);
  }
  return (
    <div className="dash-library">
      <div className="dash-bar">
        <p className="muted small">Все дашборды, сохранённые в ваших чатах.</p>
        <button
          type="button"
          className="btn btn-secondary btn-sm"
          disabled={status === "loading"}
          onClick={refresh}
        >
          <Icon name="retry" />
          Обновить
        </button>
      </div>
      {status === "loading" && (
        <p className="muted center" role="status">
          Загружаем дашборды…
        </p>
      )}
      {status === "error" && (
        <div className="err-box" role="alert">
          <p>
            <Icon name="alert" />
            Не удалось загрузить дашборды. Попробуйте обновить список.
          </p>
        </div>
      )}
      {status === "ready" && items.length === 0 && (
        <p className="muted center">
          Пока нет сохранённых дашбордов. Прикрепите CSV или подключите таблицу
          во вкладке источников, затем попросите в чате: «Создай дашборд по этим
          данным».
        </p>
      )}
      {items.length > 0 && (
        <ul className="dash-grid">
          {items.map((item) => {
            const chat = chats.find((c) => c.serverId === item.chat_id);
            return (
              <DashboardCard
                key={item.id}
                chart={item}
                subtitle={item.chat_title}
                actions={
                  <>
                    <a
                      className="btn btn-secondary btn-sm"
                      href={assetUrl(item.url)}
                      download
                    >
                      Скачать PNG
                    </a>
                    {chat && (
                      <button
                        type="button"
                        className="btn btn-secondary btn-sm"
                        onClick={() => onOpenChat(chat.id)}
                      >
                        Перейти в чат
                      </button>
                    )}
                  </>
                }
              />
            );
          })}
        </ul>
      )}
    </div>
  );
}
