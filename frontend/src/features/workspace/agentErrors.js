import axios from "axios";

// Понятное сообщение об ошибке запроса к нейросети.
export function getAgentErrorText(error) {
  if (!axios.isAxiosError(error)) return null;
  if (error.code === "ECONNABORTED") return "Нейросеть отвечает слишком долго.";
  const status = error.response?.status;
  if (!status) return "Сервер не отвечает. Проверьте, что бэкенд запущен.";
  switch (status) {
    case 401:
      return "Сессия истекла. Войдите в аккаунт снова.";
    case 404:
      return "Чат не найден на сервере.";
    case 409: {
      const detail = error.response?.data?.detail;
      return detail?.message ?? "Агент ещё обрабатывает предыдущий запрос.";
    }
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
