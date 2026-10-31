import { useEffect, useRef, useState } from "react";
import Icon from "../common/Icon";
import { MAX_FILE_MB } from "../../features/workspace/agentErrors";

export default function ChatComposer({ pending, stopping, onStop, onSend, notify }) {
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
    event.target.value = "";
    const file = selected[0];
    if (!file) return;
    // Бэкенд принимает один CSV-файл.
    if (!file.name.toLowerCase().endsWith(".csv")) {
      notify("Можно прикрепить только CSV-файл.");
      return;
    }
    if (file.size > MAX_FILE_MB * 1024 * 1024) {
      notify(`Файл больше ${MAX_FILE_MB} МБ. Загрузите файл поменьше.`);
      return;
    }
    if (selected.length > 1) notify("Можно прикрепить только один файл.");
    setFiles([file]);
  }
  return (
    <div className="composer-wrap">
      <form className="composer" onSubmit={send}>
        {["tl", "tr", "bl", "br"].map((corner) => (
          <span key={corner} className={`corner-deco ${corner}`} aria-hidden="true">
            ✻
          </span>
        ))}
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
          placeholder="Спросите Aster о данных, отчётах или анализе…"
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
            accept=".csv,text/csv"
            hidden
            onChange={attach}
          />
          {pending && onStop ? <button type="button" className="send-btn stop-btn" disabled={stopping}
            aria-label={stopping ? "Останавливаем ответ" : "Остановить ответ"}
            title={stopping ? "Останавливаем ответ…" : "Остановить ответ"}
            aria-busy={stopping}
            onClick={() => onStop().catch(() => notify("Не удалось подтвердить отмену. Повторите остановку."))}>
            <Icon name="stop" />
          </button> : <button
            type="submit"
            className="send-btn"
            aria-label="Отправить сообщение"
            disabled={!text.trim() || pending || submitting}
          >
            <Icon name="send" />
          </button>}
        </div>
      </form>
      <p className="muted small center disclaimer">
        Aster может ошибаться. К сообщению можно прикрепить один CSV-файл до {MAX_FILE_MB} МБ.
      </p>
    </div>
  );
}
