import type { EChartsOption } from "echarts";

export interface ColumnSummary {
  name: string;
  dtype: string;
  non_null: number;
  sample_values: Array<string | number | null>;
}

export type PreviewRow = Record<string, string | number | boolean | null>;

export interface ChartIdea {
  title: string;
  description: string;
  chart_type: string;
  option: EChartsOption;
}

export interface Message {
  role: "user" | "assistant";
  content: string;
}

export interface UploadResponse {
  sessionId: string;
  columns: ColumnSummary[];
  preview: PreviewRow[];
}

export interface ChatResponse {
  reply: string;
  charts: ChartIdea[];
  history: Message[];
}

export type ChartAggregation = "count" | "sum" | "mean";

export interface ManualChartRequest {
  chartType: "bar" | "line" | "pie";
  groupBy?: string;
  value?: string;
  agg?: ChartAggregation;
}

export interface ManualChartResponse {
  message: string;
  chart: ChartIdea;
  charts: ChartIdea[];
}
