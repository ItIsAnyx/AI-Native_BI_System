import Icon from "../common/Icon";

const suggestions = [
  "Составить подробный чек-лист",
  "Написать черновик письма команде",
  "Найти риски и пути их снижения",
];
const steps = [
  [
    "Уточните цель и критерии успеха",
    "Сформулируйте результат в одном предложении и определите 2–3 измеримых показателя.",
  ],
  [
    "Разбейте работу на этапы",
    "Выделите короткие итерации с понятными владельцами и сроками.",
  ],
  [
    "Соберите нужные материалы",
    "Подготовьте источники, примеры и ограничения, которые стоит учесть.",
  ],
  [
    "Назначьте точку проверки",
    "Запланируйте короткий обзор, чтобы вовремя скорректировать курс.",
  ],
];
export default function ChatMessage({
  message,
  onRetry,
  onSend,
  pending,
  canRetry,
}) {
  if (message.role === "user")
    return (
      <div className="msg-user">
        <div className="bubble">
          {message.text}
          {message.files?.length > 0 && (
            <p className="msg-files">
              📎 {message.files.map((f) => f.name).join(", ")}
            </p>
          )}
        </div>
      </div>
    );
  return (
    <div className="msg-ai">
      <span className="logo">
        <Icon name="spark" />
      </span>
      <div className="ai-body">
        {message.error ? (
          <div className="err-box">
            <p>
              <Icon name="alert" />
              Не удалось получить ответ. Повторите попытку.
            </p>
            {canRetry && (
              <button
                type="button"
                className="btn btn-secondary btn-sm"
                disabled={pending}
                onClick={onRetry}
              >
                <Icon name="retry" />
                Повторить
              </button>
            )}
          </div>
        ) : message.source !== "demo" ? (
          <p className="assistant-text">{message.text}</p>
        ) : (
          <>
            <h3>Предлагаемый план действий</h3>
            <p>
              Это демонстрационный ответ: так Aster структурирует рекомендации
              по вашему запросу.
            </p>
            <ol className="recs">
              {steps.map(([title, text]) => (
                <li key={title}>
                  <div>
                    <strong>{title}</strong>
                    <span>{text}</span>
                  </div>
                </li>
              ))}
            </ol>
            <p className="next-h">Что можно сделать дальше</p>
            <div className="chips">
              {suggestions.map((text) => (
                <button
                  type="button"
                  className="chip"
                  key={text}
                  disabled={pending}
                  onClick={() => onSend(text)}
                >
                  {text}
                </button>
              ))}
            </div>
          </>
        )}
      </div>
    </div>
  );
}
