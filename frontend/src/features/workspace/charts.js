const TYPES = {
  line: "Линия",
  scatter: "Точки",
  bar: "Столбцы",
  barh: "Столбцы горизонтально",
  area: "Область",
  pie: "Круговая",
  histogram: "Гистограмма",
  dashboard: "Дашборд",
};
const AGGREGATIONS = {
  sum: "сумма",
  mean: "среднее",
  count: "количество",
};

export const isDashboard = (chart) => chart.chart_type === "dashboard";
export const chartTypeLabel = (type) => TYPES[type] ?? type;
export const aggregationLabel = (value) => AGGREGATIONS[value] ?? null;

// Какие колонки показаны на графике: у гистограммы одна колонка, остальные — «y по x».
export function columnsLabel(chart) {
  if (chart.chart_type === "histogram")
    return `распределение ${chart.y_column || chart.x_column}`;
  return `${chart.y_column} по ${chart.x_column}`;
}

// Подпись графика для alt и заголовков.
export function chartTitle(chart) {
  if (isDashboard(chart)) return chart.title || "Дашборд";
  return chart.title || columnsLabel(chart);
}

// Все графики и дашборды чата вместе с сообщением, в котором они появились.
export function collectCharts(messages = []) {
  return messages.flatMap((message, index) =>
    (message.charts ?? []).map((chart) => ({
      chart,
      messageId: message.id,
      order: index,
    })),
  );
}
