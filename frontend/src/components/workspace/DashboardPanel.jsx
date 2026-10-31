import { assetUrl } from "../../api/endpoints/workspaceApi";
import {
  aggregationLabel,
  chartTitle,
  chartTypeLabel,
  collectCharts,
  isDashboard,
} from "../../features/workspace/charts";
import WorkspacePlaceholder from "./WorkspacePlaceholder";

function PanelList({ panels }) {
  return (
    <ul className="dash-panels">
      {panels.map((panel, index) => {
        const aggregation = aggregationLabel(panel.aggregation);
        return (
          <li key={`${panel.title}-${index}`}>
            <strong>{panel.title || `${panel.y_column} по ${panel.x_column}`}</strong>
            <span className="muted small">
              {chartTypeLabel(panel.chart_type)} · {panel.y_column} по{" "}
              {panel.x_column}
              {aggregation ? ` · ${aggregation}` : ""}
            </span>
          </li>
        );
      })}
    </ul>
  );
}

function DashboardCard({ item, onOpenMessage }) {
  const { chart, messageId } = item;
  const dashboard = isDashboard(chart);
  const url = assetUrl(chart.url);
  return (
    <li className="dash-card">
      <a
        className="dash-thumb"
        href={url}
        target="_blank"
        rel="noopener noreferrer"
        aria-label={`Открыть: ${chartTitle(chart)}`}
      >
        <img src={url} alt="" loading="lazy" />
      </a>
      <div className="dash-info">
        <h3>{chartTitle(chart)}</h3>
        <p className="muted small">
          {chartTypeLabel(chart.chart_type)}
          {dashboard && chart.panels?.length
            ? ` · ${chart.panels.length} панелей`
            : ""}
          {` · ${chart.plotted_points.toLocaleString("ru-RU")} точек`}
        </p>
        {dashboard && chart.panels?.length > 0 && (
          <PanelList panels={chart.panels} />
        )}
        <div className="dash-actions">
          <a
            className="btn btn-secondary btn-sm"
            href={url}
            target="_blank"
            rel="noopener noreferrer"
          >
            Открыть
          </a>
          <button
            type="button"
            className="btn btn-secondary btn-sm"
            onClick={() => onOpenMessage(messageId)}
          >
            Показать в чате
          </button>
        </div>
      </div>
    </li>
  );
}

// Галерея сохранённых дашбордов и графиков текущего чата (из его истории).
export default function DashboardPanel({ chat, onOpenMessage }) {
  if (chat?.loading)
    return (
      <p className="muted center" role="status">
        Загрузка переписки…
      </p>
    );
  const items = collectCharts(chat?.messages).reverse();
  if (!items.length)
    return (
      <WorkspacePlaceholder icon="grid" title="Dashboard">
        В этом чате пока нет графиков. Загрузите CSV и попросите построить
        дашборд — он сохранится здесь.
      </WorkspacePlaceholder>
    );
  const dashboards = items.filter((i) => isDashboard(i.chart));
  const charts = items.filter((i) => !isDashboard(i.chart));
  return (
    <div className="dash">
      {dashboards.length > 0 && (
        <section aria-labelledby="dash-h">
          <h2 id="dash-h">Дашборды</h2>
          <ul className="dash-grid">
            {dashboards.map((item) => (
              <DashboardCard key={item.chart.id} item={item} onOpenMessage={onOpenMessage} />
            ))}
          </ul>
        </section>
      )}
      {charts.length > 0 && (
        <section aria-labelledby="charts-h">
          <h2 id="charts-h">Графики</h2>
          <ul className="dash-grid">
            {charts.map((item) => (
              <DashboardCard key={item.chart.id} item={item} onOpenMessage={onOpenMessage} />
            ))}
          </ul>
        </section>
      )}
    </div>
  );
}
