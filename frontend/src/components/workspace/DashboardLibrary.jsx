import { useEffect, useState } from "react";
import { assetUrl, workspaceApi } from "../../api/endpoints/workspaceApi";

export default function DashboardLibrary({ visible, chats }) {
  const [items, setItems] = useState([]);
  const [status, setStatus] = useState("loading");
  const [revision, setRevision] = useState(0);
  useEffect(() => {
    if (!visible) return;
    let cancelled = false;
    workspaceApi.listDashboards().then((rows) => {
      if (!cancelled) { setItems(rows); setStatus("ready"); }
    }).catch(() => { if (!cancelled) setStatus("error"); });
    return () => { cancelled = true; };
  }, [visible, chats, revision]);
  return <div className="dashboard-library">
    <h2>Сохранённые дашборды</h2>
    <button className="btn btn-secondary" onClick={() => setRevision((r) => r + 1)}>Обновить</button>
    {status === "loading" && <p role="status">Загружаем дашборды…</p>}
    {status === "error" && <p role="alert">Не удалось загрузить дашборды. Попробуйте обновить список.</p>}
    {status === "ready" && items.length === 0 && <p>Пока нет сохранённых дашбордов. Прикрепите CSV или подключите таблицу во вкладке источников, затем попросите в чате: «Создай дашборд по этим данным».</p>}
    {items.map((item) => <figure className="dashboard-card" key={item.id}>
      <figcaption><strong>{item.title || "Дашборд"}</strong><p>{item.chat_title}</p></figcaption>
      <a href={assetUrl(item.url)} target="_blank" rel="noopener noreferrer">
        <img src={assetUrl(item.url)} alt={item.title || "Дашборд"} loading="lazy" />
      </a>
      <a className="btn btn-secondary" href={assetUrl(item.url)} download>Скачать PNG</a>
    </figure>)}
  </div>;
}
