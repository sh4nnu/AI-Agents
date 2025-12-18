import type { ChartIdea } from "../types";
import ChartCard from "./ChartCard";

interface ChartGridProps {
  charts: ChartIdea[];
}

const preferredSlots: Array<{
  expectedType: string | null;
  label: string;
}> = [
  { expectedType: "bar", label: "Bar chart" },
  { expectedType: "line", label: "Line chart" },
  { expectedType: "pie", label: "Pie chart" },
  // { expectedType: null, label: "Chart 4" },
  // { expectedType: null, label: "Chart 5" },
  // { expectedType: null, label: "Chart 6" }
];

const normalizeType = (chart: ChartIdea | null) => {
  if (!chart) {
    return "";
  }
  if (chart.chart_type) {
    return chart.chart_type.toLowerCase();
  }
  const series = Array.isArray((chart.option as any)?.series)
    ? ((chart.option as any)?.series as Array<{ type?: string }>)
    : [];
  const firstType = series.find((entry) => typeof entry?.type === "string")
    ?.type;
  return firstType?.toLowerCase() ?? "";
};

const ChartGrid = ({ charts }: ChartGridProps) => {
  const remaining = [...charts];

  const claimChart = (expectedType: string | null) => {
    if (!expectedType) {
      return remaining.shift() ?? null;
    }
    for (let i = remaining.length - 1; i >= 0; i -= 1) {
      if (normalizeType(remaining[i]).includes(expectedType)) {
        return remaining.splice(i, 1)[0];
      }
    }
    return null;
  };

  const slots = preferredSlots.map((slot) => ({
    chart: claimChart(slot.expectedType),
    expectedType: slot.expectedType
  }));

  return (
    <section className="panel">
      <div className="panel-header">
        <div>
          <h2>4. Chart canvas</h2>
          <p className="panel-hint">
            Up to three Apache ECharts configs returned by the agent live here.
          </p>
        </div>
      </div>
      <div className="chart-grid">
        {slots.map((slot, index) => (
          <ChartCard
            key={`${slot.chart?.title ?? "placeholder"}-${index}`}
            chart={slot.chart ?? null}
            index={index}
            expectedType={slot.expectedType}
          />
        ))}
      </div>
    </section>
  );
};

export default ChartGrid;
