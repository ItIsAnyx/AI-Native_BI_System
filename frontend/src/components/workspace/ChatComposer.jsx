import { useEffect, useRef, useState } from "react";
import Icon from "../common/Icon";

export default function ChatComposer({ pending, onSend, notify }) {
  const [text, setText] = useState("");
  const [files, setFiles] = useState([]);
  const [submitting, setSubmitting] = useState(false);
  const prompt = useRef(null);
  const fileInput = useRef(null);
  useEffect(() => {
    function resize() {
      const input = prompt.current;
      if (!input) return;
      input.style.height = "auto";
      input.style.height = `${Math.min(input.scrollHeight + 2, 200)}px`;
      input.style.overflowY = input.scrollHeight > 200 ? "auto" : "hidden";
    }
    resize();
    window.addEventListener("resize", resize);
    return () => window.removeEventListener("resize", resize);
  }, [text]);
  async function send(event) {
    event?.preventDefault();
    if (!text.trim() || pending || submitting) return;
    setSubmitting(true);
    try {
      if (await onSend(text, files)) {
        setText("");
        setFiles([]);
        prompt.current?.focus();
      }
    } finally {
      setSubmitting(false);
    }
  }
  function attach(event) {
    const selected = [...event.target.files];
    setFiles((previous) => {
      const combined = [...previous];
      selected.forEach((file) => {
        if (
          !combined.some(
            (f) =>
              f.name === file.name &&
              f.size === file.size &&
              f.lastModified === file.lastModified,
          )
        )
          combined.push(file);
      });
      return combined.slice(0, 5);
    });
    if (selected.length + files.length > 5)
      notify("Можно прикрепить до 5 файлов.");
    event.target.value = "";
  }
  return (
    <div className="composer-wrap">
      <form className="composer" onSubmit={send}>
        <div className="attachments">
          {files.map((file, index) => (
            <span key={`${file.name}-${index}`} className="att">
              <Icon name="file" />
              <span>{file.name}</span>
              <button
                type="button"
                aria-label={`Убрать вложение ${file.name}`}
                onClick={() => setFiles(files.filter((_, i) => i !== index))}
              >
                <Icon name="x" />
              </button>
            </span>
          ))}
        </div>
        <label htmlFor="prompt" className="sr-only">
          Сообщение для Aster
        </label>
        <textarea
          ref={prompt}
          id="prompt"
          rows={1}
          value={text}
          onChange={(e) => setText(e.target.value)}
          placeholder="Спросите Aster о плане, тексте или исследовании…"
          onKeyDown={(e) => {
            if (
              e.key === "Enter" &&
              !e.shiftKey &&
              !e.nativeEvent.isComposing
            ) {
              e.preventDefault();
              void send();
            }
          }}
        />
        <div className="composer-row">
          <button
            type="button"
            className="icon-btn"
            aria-label="Прикрепить файл"
            onClick={() => fileInput.current?.click()}
          >
            <Icon name="clip" />
          </button>
          <input
            ref={fileInput}
            type="file"
            hidden
            multiple
            onChange={attach}
          />
          <span className="muted small kbd-hint">
            Enter — отправить · Shift+Enter — новая строка
          </span>
          <button
            type="submit"
            className="send-btn"
            aria-label="Отправить сообщение"
            disabled={!text.trim() || pending || submitting}
          >
            <Icon name="send" />
          </button>
        </div>
      </form>
      <p className="muted small center disclaimer">
        Ответы пока демонстрационные, файлы не отправляются на сервер. «/error»
        покажет ошибку.
      </p>
    </div>
  );
}
