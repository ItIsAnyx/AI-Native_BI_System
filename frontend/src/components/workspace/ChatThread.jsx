import { useEffect, useRef } from "react";
import Icon from "../common/Icon";
import AiAvatar from "./AiAvatar";
import ChatMessage from "./ChatMessage";

export default function ChatThread({ chat, onSend, onRetry, onReload }) {
  const thread = useRef(null);
  useEffect(() => {
    if (thread.current) thread.current.scrollTop = thread.current.scrollHeight;
  }, [chat?.id, chat?.messages.length, chat?.pending]);
  const uploading = chat?.uploadProgress != null && chat.uploadProgress < 1;
  return (
    <div
      ref={thread}
      className="thread"
      role="log"
      aria-live="polite"
      aria-label="Переписка"
    >
      {chat?.loading && (
        <p className="muted center" role="status">
          Загрузка переписки…
        </p>
      )}
      {chat?.loadError && (
        <div className="err-box">
          <p>
            <Icon name="alert" />
            Не удалось загрузить переписку.
          </p>
          <button
            type="button"
            className="btn btn-secondary btn-sm"
            onClick={onReload}
          >
            <Icon name="retry" />
            Повторить
          </button>
        </div>
      )}
      {!chat?.messages.length && !chat?.loading && !chat?.loadError && (
        <div className="empty">
          <div className="empty-aster" aria-hidden="true">
            <i className="e-dot center" />
            {[1, 2, 3, 4, 5, 6, 7, 8].map((i) => (
              <i key={i} className="e-dot" />
            ))}
          </div>
          <h2>Чем займёмся сегодня?</h2>
          <p className="muted empty-sub">
            Загрузите CSV-файл с данными или задайте вопрос на естественном
            языке — Aster построит отчёт, графики и рекомендации.
          </p>
          <div className="chips">
            {[
              "Проанализировать продажи",
              "Построить дашборд",
              "Найти аномалии в данных",
            ].map((text) => (
              <button
                type="button"
                key={text}
                className="chip"
                onClick={() => onSend(text)}
              >
                {text}
              </button>
            ))}
          </div>
        </div>
      )}
      {chat?.messages.map((message, index) => (
        <ChatMessage
          key={message.id}
          message={message}
          pending={chat.pending}
          canRetry={index === chat.messages.length - 1}
          onRetry={onRetry}
        />
      ))}
      {chat?.pending && (
        <div className="msg-ai" role="status" aria-label="Aster печатает">
          <AiAvatar />
          <div className="ai-body">
            {uploading ? (
              <div className="upload-progress">
                <p className="muted small">
                  Загрузка файла… {Math.round(chat.uploadProgress * 100)}%
                </p>
                <progress max="1" value={chat.uploadProgress} />
              </div>
            ) : (
              <div className="typing" aria-hidden="true">
                <i />
                <i />
                <i />
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
