import Icon from "../common/Icon";
import WorkspacePlaceholder from "./WorkspacePlaceholder";
import { assetUrl } from "../../api/endpoints/workspaceApi";

// Файлы (CSV), загруженные в текущий чат. Список приходит с сервера вместе с ответами чата.
export default function SourcesPanel({ chat }) {
  const sources = chat?.sources ?? [];
  if (!sources.length)
    return (
      <WorkspacePlaceholder icon="db" title="Data sources">
        В этом чате пока нет файлов. Прикрепите CSV к сообщению, и он появится
        здесь.
      </WorkspacePlaceholder>
    );
  return (
    <div className="sources">
      <h2>Источники данных</h2>
      <ul className="sources-list">
        {sources.map((source) => (
          <li key={source.id}>
            <span className="ph-ic sm">
              <Icon name="file" />
            </span>
            <div>
              <strong>{source.name}</strong>
              <span className="muted small">
                {source.type.toUpperCase()}
                {source.description ? ` · ${source.description}` : ""}
              </span>
            </div>
            <a
              className="btn btn-secondary btn-sm"
              href={assetUrl(`/agent/sources/${source.id}/file`)}
              download={source.name}
            >
              Скачать
            </a>
          </li>
        ))}
      </ul>
    </div>
  );
}
