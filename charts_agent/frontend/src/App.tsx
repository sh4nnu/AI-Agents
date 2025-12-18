import { useCallback, useMemo, useState } from "react";
import { uploadDataset, sendChat, buildManualChart } from "./api";
import type {
  ChartIdea,
  ColumnSummary,
  Message,
  PreviewRow,
  ManualChartRequest
} from "./types";
import UploadPanel from "./components/UploadPanel";
import DataPreview from "./components/DataPreview";
import ChartGrid from "./components/ChartGrid";
import ChatPanel from "./components/ChatPanel";
import ChartControls from "./components/ChartControls";

function App() {
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [columns, setColumns] = useState<ColumnSummary[]>([]);
  const [preview, setPreview] = useState<PreviewRow[]>([]);
  const [charts, setCharts] = useState<ChartIdea[]>([]);
  const [history, setHistory] = useState<Message[]>([]);
  const [uploading, setUploading] = useState(false);
  const [chatLoading, setChatLoading] = useState(false);
  const [manualLoading, setManualLoading] = useState(false);
  const [status, setStatus] = useState("Upload a dataset to begin.");
  const [error, setError] = useState<string | null>(null);

  const hasDataset = Boolean(sessionId);

  const handleUpload = useCallback(async (file: File) => {
    setUploading(true);
    setError(null);
    setStatus("Uploading dataset...");
    try {
      const result = await uploadDataset(file);
      setSessionId(result.sessionId);
      setColumns(result.columns);
      setPreview(result.preview);
      setCharts([]);
      setHistory([]);
      setStatus("Dataset loaded. Ask the agent for insights.");
    } catch (err) {
      console.error(err);
      setError(
        err instanceof Error ? err.message : "Failed to upload dataset."
      );
      setStatus("Upload failed. Please try another file.");
    } finally {
      setUploading(false);
    }
  }, []);

  const handleSendMessage = useCallback(
    async (message: string) => {
      if (!sessionId) {
        setError("Upload a dataset before chatting with the agent.");
        return;
      }
      setChatLoading(true);
      setError(null);
      setStatus("Agent is exploring the dataset...");
      const userMessage: Message = { role: "user", content: message };
      setHistory((prev) => [...prev, userMessage]);
      try {
        const response = await sendChat(sessionId, message);
        setCharts(response.charts ?? []);
        setHistory(response.history ?? []);
        setStatus("Charts updated. Ask another question to refine.");
      } catch (err) {
        console.error(err);
        setHistory((prev) => prev.slice(0, -1));
        setError(err instanceof Error ? err.message : "Chat request failed.");
        setStatus("Agent error. Try sending your message again.");
      } finally {
        setChatLoading(false);
      }
    },
    [sessionId]
  );

  const handleBuildManualChart = useCallback(
    async (payload: ManualChartRequest) => {
      if (!sessionId) {
        setError("Upload a dataset before building charts.");
        return;
      }
      setManualLoading(true);
      setError(null);
      setStatus("Building chart from your columns...");
      try {
        const response = await buildManualChart(sessionId, payload);
        setCharts(response.charts ?? []);
        setStatus(response.message ?? "Chart updated.");
      } catch (err) {
        console.error(err);
        setError(
          err instanceof Error ? err.message : "Failed to build manual chart."
        );
        setStatus("Manual chart failed. Adjust selections and retry.");
      } finally {
        setManualLoading(false);
      }
    },
    [sessionId]
  );

  const helperText = useMemo(() => {
    if (error) {
      return error;
    }
    return status;
  }, [error, status]);

  return (
    <div className="app-shell">
      <header className="app-header">
        <div>
          <h1>Charts Agent</h1>
          <p>
            Upload structured data, brainstorm charts with AI, and get Apache
            ECharts options instantly.
          </p>
        </div>
        <div className="status-pill">
          {hasDataset ? "Session active" : "Awaiting dataset"}
        </div>
      </header>

      <p className={`status-text ${error ? "status-error" : ""}`}>
        {helperText}
      </p>

      <div className="app-layout">
        <main className="workspace">
          <UploadPanel
            onUpload={handleUpload}
            uploading={uploading}
            sessionReady={hasDataset}
          />
          <DataPreview columns={columns} preview={preview} />
          <ChartControls
            columns={columns}
            disabled={!hasDataset}
            loading={manualLoading}
            onBuild={handleBuildManualChart}
          />
          <ChartGrid charts={charts} />
        </main>
        <aside className="chat-sidebar">
          <ChatPanel
            history={history}
            disabled={!hasDataset}
            loading={chatLoading}
            onSend={handleSendMessage}
            sessionReady={hasDataset}
          />
        </aside>
      </div>
    </div>
  );
}

export default App;
