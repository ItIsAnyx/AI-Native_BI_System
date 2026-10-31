import { assetUrl } from "../../api/endpoints/workspaceApi";
import { chartTitle, isDashboard } from "../../features/workspace/charts";

export default function ChartFigure({ chart }) {
  const title = chartTitle(chart);
  return (
    <figure className="chart">
      <a href={assetUrl(chart.url)} target="_blank" rel="noopener noreferrer">
        <img
          src={assetUrl(chart.url)}
          alt={isDashboard(chart) ? title : `График: ${title}`}
          loading="lazy"
        />
      </a>
      {isDashboard(chart) && <figcaption>{chart.title}</figcaption>}
      {chart.truncated && (
        <figcaption>
          Показано {chart.plotted_points} из {chart.available_points} точек.
        </figcaption>
      )}
    </figure>
  );
}
