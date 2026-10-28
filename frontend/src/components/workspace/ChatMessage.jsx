import { lazy, Suspense } from "react";
import Icon from "../common/Icon";
import ChartFigure from "./ChartFigure";
import AiAvatar from "./AiAvatar";

// Библиотека разметки (react-markdown) подгружается отдельным файлом, когда нужен первый ответ ассистента.
const Markdown = lazy(() => import("./Markdown"));

export default function ChatMessage({
  message,
  onRetry,
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
    <div className="msg-ai" id={`msg-${message.id}`}>
      <AiAvatar />
      <div className="ai-body">
        {message.error ? (
          <div className="err-box">
            <p>
              <Icon name="alert" />
              {message.errorText ?? "Не удалось получить ответ. Повторите попытку."}
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
        ) : (
          <>
            <Suspense fallback={<p className="assistant-text">{message.text}</p>}>
              <Markdown>{message.text}</Markdown>
            </Suspense>
            {message.charts?.map((chart) => (
              <ChartFigure chart={chart} key={chart.id} />
            ))}
          </>
        )}
      </div>
    </div>
  );
}
