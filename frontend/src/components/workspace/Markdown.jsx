import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

// Ссылки из ответов открываем в новой вкладке и без передачи referrer.
const components = {
  // eslint-disable-next-line no-unused-vars
  a: ({ node, ...props }) => (
    <a {...props} target="_blank" rel="noopener noreferrer nofollow" />
  ),
  // Картинки из ответа: ленивая загрузка, клик открывает оригинал в новой вкладке.
  // eslint-disable-next-line no-unused-vars
  img: ({ node, alt, src, ...props }) => (
    <a href={src} target="_blank" rel="noopener noreferrer">
      <img {...props} src={src} alt={alt ?? ""} loading="lazy" />
    </a>
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
