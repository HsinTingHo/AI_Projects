export type UploadedReport = {
  id: string;
  filename: string;
  status: "uploading" | "queued" | "processing" | "ready" | "failed";
};

export async function uploadReport(file: File): Promise<UploadedReport> {
  console.info("[upload] Starting PDF upload", { bytes: file.size });
  const body = new FormData();
  body.append("file", file);
  const base = (process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000").replace(/\/$/, "");
  let response: Response;
  try {
    response = await fetch(`${base}/reports`, { method: "POST", body });
  } catch {
    console.error("[upload] Network request failed");
    throw new Error("Couldn’t reach the upload server. Check your connection and that the backend is running.");
  }
  console.info("[upload] Server responded", { status: response.status });
  const data = await response.json().catch(() => null);
  if (!response.ok) {
    const detail = data?.detail;
    const message = typeof detail === "string" ? detail
      : Array.isArray(detail) ? detail.map(item => item.msg).filter(Boolean).join("; ") : "";
    console.warn("[upload] Server rejected upload", { status: response.status });
    throw new Error(message || `Upload failed (${response.status}). Please try again.`);
  }
  if (!data || typeof data.id !== "string" || typeof data.filename !== "string" ||
      !["uploading", "queued", "processing", "ready", "failed"].includes(data.status)) {
    console.error("[upload] Unexpected response format");
    throw new Error("The server accepted the upload but returned an unexpected response. Check the saved report before retrying.");
  }
  console.info("[upload] Upload saved", { reportId: data.id, status: data.status });
  return data;
}
