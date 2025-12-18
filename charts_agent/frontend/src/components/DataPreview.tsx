import type { ColumnSummary, PreviewRow } from "../types";

interface DataPreviewProps {
  columns: ColumnSummary[];
  preview: PreviewRow[];
}

const DataPreview = ({ columns, preview }: DataPreviewProps) => {
  if (!columns.length) {
    return (
      <section className="panel">
        <h2>2. Dataset profile</h2>
        <p className="panel-hint">
          Upload a file to inspect column types, non-null counts, and a preview
          of the first rows.
        </p>
      </section>
    );
  }

  const visiblePreview = preview.slice(0, 8);

  return (
    <section className="panel">
      <div className="panel-header">
        <h2>2. Dataset profile</h2>
        <span className="panel-meta">
          {columns.length} columns · showing first {visiblePreview.length} rows
        </span>
      </div>
      <div className="columns-grid">
        {columns.map((column) => (
          <div className="column-card" key={column.name}>
            <strong>{column.name}</strong>
            <span className="column-type">{column.dtype}</span>
            <span className="column-meta">
              Non-null: {column.non_null.toLocaleString()}
            </span>
            <span className="column-meta">
              Sample: {column.sample_values.join(", ")}
            </span>
          </div>
        ))}
      </div>
      <div className="table-wrapper">
        <table>
          <thead>
            <tr>
              {Object.keys(visiblePreview[0] ?? {}).map((key) => (
                <th key={key}>{key}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {visiblePreview.map((row, rowIndex) => (
              <tr key={rowIndex}>
                {Object.keys(row).map((key) => (
                  <td key={key}>{String(row[key] ?? "")}</td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
};

export default DataPreview;
