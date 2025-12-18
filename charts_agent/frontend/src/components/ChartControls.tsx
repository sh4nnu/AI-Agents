import { useEffect, useMemo, useState } from "react";
import type { ColumnSummary, ManualChartRequest } from "../types";

interface ChartControlsProps {
  columns: ColumnSummary[];
  disabled: boolean;
  loading: boolean;
  onBuild: (payload: ManualChartRequest) => Promise<void> | void;
}

const isNumeric = (dtype: string) =>
  /int|float|double|decimal|number/i.test(dtype);

const chartOptions: Array<{ value: ManualChartRequest["chartType"]; label: string }> = [
  { value: "bar", label: "Bar" },
  { value: "line", label: "Line" },
  { value: "pie", label: "Pie" }
];

const aggregationOptions: Array<{ value: ManualChartRequest["agg"]; label: string }> = [
  { value: "count", label: "Count" },
  { value: "sum", label: "Sum" },
  { value: "mean", label: "Average" }
];

const ChartControls = ({
  columns,
  disabled,
  loading,
  onBuild
}: ChartControlsProps) => {
  const groupableColumns = columns.map((col) => col.name);
  const numericColumns = useMemo(
    () => columns.filter((col) => isNumeric(col.dtype)).map((col) => col.name),
    [columns]
  );

  const [chartType, setChartType] =
    useState<ManualChartRequest["chartType"]>("bar");
  const [groupBy, setGroupBy] = useState<string>("");
  const [value, setValue] = useState<string>("");
  const [agg, setAgg] = useState<ManualChartRequest["agg"]>("count");

  const requiresValue = agg !== "count";
  const ready =
    Boolean(groupBy) && (!requiresValue || Boolean(value)) && !disabled;

  useEffect(() => {
    if (!groupBy && groupableColumns.length) {
      setGroupBy(groupableColumns[0]);
    }
  }, [groupBy, groupableColumns]);

  useEffect(() => {
    if (!value && numericColumns.length && agg !== "count") {
      setValue(numericColumns[0]);
    }
    if (agg === "count") {
      setValue("");
    }
  }, [value, numericColumns, agg]);

  const handleSubmit = () => {
    if (!groupBy) {
      return;
    }
    void onBuild({
      chartType,
      groupBy,
      value: requiresValue ? value : undefined,
      agg
    });
  };

  return (
    <section className="panel">
      <div className="panel-header">
        <div>
          <h2>3. Build a chart manually</h2>
          <p className="panel-hint">
            Choose a chart type, group by a column, and aggregate a metric.
            Great for quick summaries before asking the agent to refine.
          </p>
        </div>
      </div>
      <div className="control-grid">
        <label className="control-field">
          <span>Chart type</span>
          <select
            value={chartType}
            onChange={(event) =>
              setChartType(event.target.value as ManualChartRequest["chartType"])
            }
            disabled={disabled || loading}
          >
            {chartOptions.map((option) => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>
        </label>

        <label className="control-field">
          <span>Group by column</span>
          <select
            value={groupBy}
            onChange={(event) => setGroupBy(event.target.value)}
            disabled={disabled || loading || !groupableColumns.length}
          >
            <option value="">
              {groupableColumns.length
                ? "Select a column"
                : "Upload data to enable"}
            </option>
            {groupableColumns.map((name) => (
              <option key={name} value={name}>
                {name}
              </option>
            ))}
          </select>
        </label>

        <label className="control-field">
          <span>Aggregation</span>
          <select
            value={agg}
            onChange={(event) =>
              setAgg(event.target.value as ManualChartRequest["agg"])
            }
            disabled={disabled || loading}
          >
            {aggregationOptions.map((option) => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>
        </label>

        <label className="control-field">
          <span>Value column</span>
          <select
            value={value}
            onChange={(event) => setValue(event.target.value)}
            disabled={
              disabled || loading || agg === "count" || !numericColumns.length
            }
          >
            <option value="">
              {agg === "count"
                ? "Not needed for counts"
                : numericColumns.length
                ? "Select a numeric column"
                : "No numeric columns detected"}
            </option>
            {numericColumns.map((name) => (
              <option key={name} value={name}>
                {name}
              </option>
            ))}
          </select>
        </label>
      </div>
      <div className="control-actions">
        <button
          type="button"
          onClick={handleSubmit}
          disabled={!ready || loading}
        >
          {loading ? "Building…" : "Build chart"}
        </button>
        <p className="panel-hint">
          Tip: Use this to create a baseline, then ask the agent to customize
          colors, labels, or add more series.
        </p>
      </div>
    </section>
  );
};

export default ChartControls;
