"use client";

import { useId, useRef, useState, type ChangeEvent } from "react";
import Button from "../ui/Button";

export type UploadReportButtonProps = {
  onUpload: (file: File) => Promise<void>;
  maxSizeMB?: number;
  disabled?: boolean;
  successMessage?: string;
};

export default function UploadReportButton({ onUpload, maxSizeMB = 25, disabled = false, successMessage }: UploadReportButtonProps) {
  const input = useRef<HTMLInputElement>(null);
  const busy = useRef(false);
  const messageId = useId();
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");

  async function handleFile(event: ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];
    event.target.value = "";
    if (!file || busy.current) return;
    setError("");
    setMessage("");
    if (!file.name.toLowerCase().endsWith(".pdf")) { setError("Choose a PDF report."); return; }
    if (!file.size) { setError("This file is empty. Choose another PDF."); return; }
    if (file.size > maxSizeMB * 1024 * 1024) { setError(`Choose a PDF smaller than ${maxSizeMB} MB.`); return; }
    busy.current = true;
    setUploading(true);
    try {
      await onUpload(file);
      setMessage(successMessage ?? `${file.name} uploaded. Check its processing status below.`);
    } catch {
      setError("Upload failed. Please try again.");
    } finally {
      busy.current = false;
      setUploading(false);
    }
  }

  return (
    <div className="space-y-2">
      <input ref={input} type="file" accept="application/pdf,.pdf" hidden aria-label="Choose report PDF" disabled={disabled || uploading} onChange={handleFile} />
      <Button fullWidth disabled={disabled} loading={uploading} loadingText="Uploading…" aria-describedby={messageId} onClick={() => input.current?.click()}>
        <span aria-hidden="true">＋</span> Upload report
      </Button>
      <p id={messageId} className="text-xs text-[#757a6d] dark:text-[#adb5a1]">PDF · Up to {maxSizeMB} MB</p>
      {error && <p role="alert" className="text-xs text-red-700 dark:text-red-300">{error}</p>}
      <p role="status" className="break-words text-xs text-[#757a6d] dark:text-[#adb5a1]">{message}</p>
    </div>
  );
}
