import ReactECharts from "echarts-for-react";
import type { EChartsOption } from "echarts";
import type { ChartIdea } from "../types";

const fallbackOptions: Record<string, EChartsOption> = {
  bar: {
    title: { text: "Sample Bar Chart" },
    tooltip: { trigger: "axis" },
    xAxis: {
      type: "category",
      data: ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
    },
    yAxis: { type: "value" },
    series: [
      {
        name: "Value",
        type: "bar",
        data: [120, 200, 150, 80, 70, 110, 130]
      }
    ]
  },
  line: {
    title: { text: "Sample Line Chart" },
    tooltip: { trigger: "axis" },
    xAxis: {
      type: "category",
      data: ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul"]
    },
    yAxis: { type: "value" },
    series: [
      {
        name: "Trend",
        type: "line",
        data: [820, 932, 901, 934, 1290, 1330, 1320],
        smooth: true
      }
    ]
  },
  pie: {
    title: { text: "Sample Pie Chart", left: "center" },
    tooltip: { trigger: "item" },
    legend: { bottom: 0 },
    series: [
      {
        name: "Share",
        type: "pie",
        radius: "60%",
        data: [
          { value: 1048, name: "Search" },
          { value: 735, name: "Direct" },
          { value: 580, name: "Email" },
          { value: 484, name: "Union Ads" },
          { value: 300, name: "Video Ads" }
        ]
      }
    ]
  }
};

interface ChartCardProps {
  chart: ChartIdea | null;
  index: number;
  expectedType?: string | null;
}

const getDisplayType = (chart: ChartIdea | null, fallback?: string | null) => {
  if (chart?.chart_type) {
    return chart.chart_type;
  }
  const series = Array.isArray((chart?.option as any)?.series)
    ? ((chart?.option as any)?.series as Array<{ type?: string }>)
    : [];
  const detected = series.find((entry) => typeof entry?.type === "string")
    ?.type;
  return detected ?? fallback ?? undefined;
};

const ChartCard = ({ chart, index, expectedType }: ChartCardProps) => {
  const displayType = getDisplayType(
    chart,
    expectedType ? expectedType.toUpperCase() : null
  );
  const normalizedExpected = expectedType
    ? expectedType.toLowerCase()
    : null;
  const fallbackOption =
    normalizedExpected && normalizedExpected in fallbackOptions
      ? fallbackOptions[normalizedExpected as keyof typeof fallbackOptions]
      : undefined;
  const chartOption =
    chart?.option && Object.keys(chart.option).length > 0
      ? chart.option
      : undefined;
  const optionToRender = chartOption ?? fallbackOption;

  return (
    <div className="chart-card">
      <div className="chart-card-header">
        <span className="chart-slot">Chart {index + 1}</span>
        {displayType && <span className="chart-type">{displayType}</span>}
      </div>
      {chart ? (
        <>
          <h3>{chart.title}</h3>
          <p className="chart-description">{chart.description}</p>
          <div className="chart-preview">
            <ReactECharts
              option={optionToRender ?? {}}
              notMerge
              lazyUpdate
              style={{ height: "220px" }}
            />
          </div>
        </>
      ) : optionToRender ? (
        <>
          <h3>Sample {expectedType?.toUpperCase()} layout</h3>
          <p className="chart-description">
            Upload data and ask the agent to replace this sample with a custom{" "}
            {expectedType?.toUpperCase()} chart.
          </p>
          <div className="chart-preview">
            <ReactECharts
              option={optionToRender}
              notMerge
              lazyUpdate
              style={{ height: "220px" }}
            />
          </div>
        </>
      ) : (
        <div className="chart-placeholder">
          {expectedType
            ? `Waiting for a ${expectedType.toUpperCase()} idea. Ask the agent to craft one.`
            : "No chart here yet. Ask the agent for another visualization idea."}
        </div>
      )}
    </div>
  );
};

export default ChartCard;
