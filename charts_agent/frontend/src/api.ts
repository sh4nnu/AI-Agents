import type {
  ChatResponse,
  ManualChartRequest,
  ManualChartResponse,
  UploadResponse
} from "./types";

const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL?.replace(/\/$/, "") ?? "http://localhost:8000";

async function handleResponse<T>(response: Response): Promise<T> {
  if (!response.ok) {
    const text = await response.text();
    throw new Error(text || `Request failed with status ${response.status}`);
  }
  return (await response.json()) as T;
}

export async function uploadDataset(file: File): Promise<UploadResponse> {
  const formData = new FormData();
  formData.append("file", file);
  const response = await fetch(`${API_BASE_URL}/upload`, {
    method: "POST",
    body: formData
  });
  const data = await handleResponse<{
    session_id: string;
    columns: UploadResponse["columns"];
    preview: UploadResponse["preview"];
  }>(response);
  return {
    sessionId: data.session_id,
    columns: data.columns ?? [],
    preview: data.preview ?? []
  };
}

export async function sendChat(
  sessionId: string,
  message: string
): Promise<ChatResponse> {
  const response = await fetch(`${API_BASE_URL}/chat`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json"
    },
    body: JSON.stringify({
      session_id: sessionId,
      message
    })
  });
  return handleResponse<ChatResponse>(response);
}

export async function buildManualChart(
  sessionId: string,
  payload: ManualChartRequest
): Promise<ManualChartResponse> {
  const response = await fetch(`${API_BASE_URL}/chart/manual`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json"
    },
    body: JSON.stringify({
      session_id: sessionId,
      chart_type: payload.chartType,
      group_by: payload.groupBy,
      value: payload.value,
      agg: payload.agg
    })
  });
  return handleResponse<ManualChartResponse>(response);
}
