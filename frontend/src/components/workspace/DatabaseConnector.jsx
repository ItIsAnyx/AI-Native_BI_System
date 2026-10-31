import { useEffect, useState } from "react";
import { workspaceApi } from "../../api/endpoints/workspaceApi";

export default function DatabaseConnector({ onConnect }) {
  const [connections, setConnections] = useState([]);
  const [connection, setConnection] = useState("");
  const [tables, setTables] = useState([]);
  const [table, setTable] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  useEffect(() => {
    let cancelled = false;
    workspaceApi.listConnections().then((rows) => { if (!cancelled) setConnections(rows); })
      .catch(() => { if (!cancelled) setError("Не удалось загрузить подключения."); });
    return () => { cancelled = true; };
  }, []);
  async function chooseConnection(value) {
    setConnection(value); setTables([]); setTable(""); setError("");
    if (!value) return;
    setBusy(true);
    try { setTables(await workspaceApi.listTables(value)); }
    catch { setError("Не удалось прочитать список таблиц. Проверьте подключение и права доступа."); }
    finally { setBusy(false); }
  }
  async function connect(event) {
    event.preventDefault(); setError(""); setBusy(true);
    try { await onConnect({ connection_id: connection, ...tables[Number(table)] }); }
    catch (e) { setError(e.response?.data?.detail || "Не удалось подключить таблицу."); }
    finally { setBusy(false); }
  }
  return <form className="database-connector" onSubmit={connect}>
    <h3>Подключить таблицу PostgreSQL</h3>
    {connections.length === 0 ? <p>Аналитические подключения ещё не настроены. CSV можно прикрепить к сообщению в чате.</p> : <>
      <label>Подключение <select value={connection} disabled={busy} onChange={(e) => chooseConnection(e.target.value)}>
        <option value="">Выберите подключение</option>
        {connections.map((c) => <option key={c.id} value={c.id}>{c.name}</option>)}
      </select></label>
      <label>Таблица <select value={table} disabled={busy || !connection} onChange={(e) => setTable(e.target.value)}>
        <option value="">Выберите таблицу</option>
        {tables.map((t, i) => <option key={`${t.schema}.${t.table}`} value={i}>{t.schema}.{t.table}</option>)}
      </select></label>
      <button className="btn btn-primary" disabled={busy || !connection || table === ""}>Подключить</button>
      {busy && <p role="status">Подключаемся…</p>}
    </>}
    {error && <p role="alert">{error}</p>}
  </form>;
}
