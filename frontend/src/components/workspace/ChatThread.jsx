import { useEffect, useRef } from "react";
import Icon from "../common/Icon";
import ChatMessage from "./ChatMessage";

export default function ChatThread({ chat, onSend, onRetry }) {
  const thread = useRef(null);
  useEffect(() => {
    if (thread.current) thread.current.scrollTop = thread.current.scrollHeight;
  }, [chat?.id, chat?.messages.length, chat?.pending]);
  return (
    <div
      ref={thread}
      className="thread"
      role="log"
      aria-live="polite"
      aria-label="Переписка"
    >
      {!chat?.messages.length && (
        <div className="empty">
          <span className="logo">
            <Icon name="spark" />
          </span>
          <h2>Чем займёмся сегодня?</h2>
          <p className="muted">
            План, текст или исследование — начните с сообщения.
          </p>
          <div className="chips">
            {[
              "Составить план проекта",
              "Написать письмо",
              "Подготовить исследование",
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
          onSend={onSend}
        />
      ))}
      {chat?.pending && (
        <div className="msg-ai" role="status" aria-label="Aster печатает">
          <span className="logo">
            <Icon name="spark" />
          </span>
          <div className="typing" aria-hidden="true">
            <i />
            <i />
            <i />
          </div>
        </div>
      )}
    </div>
  );
}
