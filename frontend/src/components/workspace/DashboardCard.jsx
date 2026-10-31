import { assetUrl } from "../../api/endpoints/workspaceApi";
import {
  aggregationLabel,
  chartTitle,
  chartTypeLabel,
  columnsLabel,
  isDashboard,
} from "../../features/workspace/charts";

function PanelList({ panels }) {
  return (
    <ul className="dash-panels">
      {panels.map((panel, index) => {
        const aggregation = aggregationLabel(panel.aggregation);
        return (
          <li key={`${panel.title}-${index}`}>
            <strong>{panel.title || columnsLabel(panel)}</strong>
            <span className="muted small">
              {chartTypeLabel(panel.chart_type)} · {columnsLabel(panel)}
              {aggregation ? ` · ${aggregation}` : ""}
            </span>
          </li>
        );
      })}
    </ul>
  );
}

// Карточка графика или дашборда: превью, описание, список панелей и кнопки действий.
// subtitle — например, название чата; actions — дополнительные кнопки.
export default function DashboardCard({ chart, subtitle, actions }) {
  const dashboard = isDashboard(chart);
  const url = assetUrl(chart.url);
  const points = chart.plotted_points;
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
        {subtitle && <p className="dash-sub small">{subtitle}</p>}
        <p className="muted small">
          {chartTypeLabel(chart.chart_type)}
          {dashboard && chart.panels?.length
            ? ` · ${chart.panels.length} панелей`
            : ""}
          {typeof points === "number"
            ? ` · ${points.toLocaleString("ru-RU")} точек`
            : ""}
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
          {actions}
        </div>
      </div>
    </li>
  );
}
