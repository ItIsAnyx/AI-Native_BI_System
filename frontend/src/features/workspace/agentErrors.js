import axios from "axios";

// Максимальный размер CSV на клиенте (МБ). Должен совпадать с MAX_FILE_SIZE_MB бэкенда.
export const MAX_FILE_MB = Number(import.meta.env.VITE_MAX_FILE_MB) || 500;

// Бэкенд отдаёт detail строкой, объектом {code, message} или списком (422).
function readDetail(error) {
  const detail = error.response?.data?.detail;
  if (typeof detail === "string") return detail;
  if (detail && typeof detail === "object" && !Array.isArray(detail))
    return detail.message ?? "";
  return "";
}

// Ошибка 400 зависит от причины, а не только от формата файла.
function badRequestText(detail) {
  if (/only csv/i.test(detail)) return "Принимаются только файлы CSV.";
  if (/too many rows/i.test(detail)) {
    const limit = detail.match(/\d+/)?.[0];
    return `В файле слишком много строк${limit ? `: максимум ${Number(limit).toLocaleString("ru-RU")}` : ""}. Загрузите часть данных.`;
  }
  if (/csv is empty/i.test(detail)) return "CSV-файл пустой: в нём нет строк с данными.";
  if (/cannot read csv/i.test(detail))
    return `Не удалось прочитать CSV: ${detail.replace(/^cannot read csv:\s*/i, "")}`;
  return "Сервер отклонил запрос. Проверьте сообщение и файл.";
}

// Понятное сообщение об ошибке запроса к нейросети.
export function getAgentErrorText(error) {
  if (!axios.isAxiosError(error)) return null;
  if (error.code === "ECONNABORTED" || error.code === "ETIMEDOUT")
    return "Ответ не пришёл вовремя. Агент мог всё ещё работать: через минуту нажмите «Повторить» — сначала проверим, не сохранился ли ответ.";
  const status = error.response?.status;
  if (!status)
    return "Нет связи с сервером. Проверьте подключение: когда оно вернётся, «Повторить» сначала проверит, не сохранился ли ответ.";
  const detail = readDetail(error);
  if (isUncertainError(error))
    return "Связь с сервером прервалась, ответ мог не прийти. «Повторить» сначала проверит, не сохранился ли он.";
  switch (status) {
    case 401:
      return "Сессия истекла. Войдите в аккаунт снова.";
    case 404:
      return "Чат или файл не найден на сервере. Обновите список чатов.";
    case 409:
      // Строка с бэкенда: «Chat changed during this request…» либо agent_busy.
      return /chat changed/i.test(detail)
        ? "Чат изменился во время запроса. Обновите страницу и повторите."
        : "Агент ещё обрабатывает предыдущий запрос. Дождитесь ответа и повторите.";
    case 400:
      return badRequestText(detail);
    case 413:
      return `Файл слишком большой (максимум ${MAX_FILE_MB} МБ).`;
    case 422:
      return /blank/i.test(detail)
        ? "Сообщение не может быть пустым."
        : "Сообщение слишком длинное или неверно оформлено.";
    case 502:
      return "Модель вернула некорректный ответ. Повторите запрос или переформулируйте его.";
    case 503:
      return "Нейросеть недоступна: проверьте, что Ollama запущена и MODEL_NAME задан.";
    case 504:
      return "Нейросеть не успела ответить. Попробуйте упростить запрос.";
    default:
      return "Не удалось получить ответ от нейросети.";
  }
}

// Неясно, дошёл ли запрос до модели: ответ мог сохраниться на сервере.
// Шлюз (прокси) при обрыве отвечает 502/503/504 без JSON с detail, в отличие от самого бэкенда.
export function isUncertainError(error) {
  if (!axios.isAxiosError(error)) return false;
  if (!error.response) return true;
  if (error.code === "ECONNABORTED" || error.code === "ETIMEDOUT") return true;
  const status = error.response.status;
  return [502, 503, 504].includes(status) && !readDetail(error);
}
