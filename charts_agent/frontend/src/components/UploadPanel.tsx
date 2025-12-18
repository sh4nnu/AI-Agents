import { ChangeEvent } from "react";

interface UploadPanelProps {
  onUpload: (file: File) => Promise<void> | void;
  uploading: boolean;
  sessionReady: boolean;
}

const UploadPanel = ({
  onUpload,
  uploading,
  sessionReady
}: UploadPanelProps) => {
  const handleFileChange = async (event: ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (file) {
      await onUpload(file);
      event.target.value = "";
    }
  };

  return (
    <section className="panel">
      <div className="panel-header">
        <div>
          <h2>1. Upload your dataset</h2>
          <p>Accepted formats: CSV, XLSX. The first 20 rows are profiled.</p>
        </div>
        <span className={`session-indicator ${sessionReady ? "ready" : ""}`}>
          {sessionReady ? "Ready" : "Waiting"}
        </span>
      </div>
      <label className="upload-button">
        <input
          type="file"
          accept=".csv,.xlsx,.xls"
          onChange={handleFileChange}
          disabled={uploading}
          hidden
        />
        {uploading ? "Uploading…" : "Choose a file"}
      </label>
      <p className="panel-hint">
        The backend keeps the session in memory, so you can iterate with the AI
        without re-uploading unless you refresh the page.
      </p>
    </section>
  );
};

export default UploadPanel;
