import axios from "axios";

// Понятное сообщение об ошибке запроса к нейросети.
export function getAgentErrorText(error) {
  if (!axios.isAxiosError(error)) return null;
  if (error.code === "ECONNABORTED") return "Нейросеть отвечает слишком долго.";
  const status = error.response?.status;
  if (!status) return "Сервер не отвечает. Проверьте, что бэкенд запущен.";
  switch (status) {
    case 400:
      return "Принимаются только CSV-файлы.";
    case 413:
      return "Файл слишком большой.";
    case 422:
      return "Не удалось обработать запрос: проверьте сообщение и файл.";
    case 503:
      return "Нейросеть недоступна: проверьте, что Ollama запущена и MODEL_NAME задан.";
    case 504:
      return "Нейросеть не успела ответить.";
    default:
      return "Не удалось получить ответ от нейросети.";
  }
}

// Данные файла бэкенд дописывает в системное сообщение; при повторной отправке того же файла убираем старый блок.
export function stripDatasetBlock(context) {
  if (context[0]?.role !== "system") return context;
  const content = context[0].content.replace(/\n*<dataset>[\s\S]*?<\/dataset>/g, "");
  return [{ ...context[0], content }, ...context.slice(1)];
}
