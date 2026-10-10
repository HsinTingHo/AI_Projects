"use client";

import { useId, useRef, useState } from "react";
import SearchInput from "../ui/SearchInput";
import ReportList from "./ReportList";
import UploadReportButton from "./UploadReportButton";
import type { Report } from "./ReportItem";

export type ReportSectionProps = {
  reports: Report[];
  selectedReportIds: string[];
  onSelectionChange: (ids: string[]) => void;
  /** Resolve after the server accepts the upload; update reports in the parent. */
  onUpload: (file: File) => Promise<void>;
  /** Resolve after deletion; remove the report and its selection from parent state. */
  onDelete?: (id: string) => Promise<void>;
  loading?: boolean;
  error?: string;
  onRetry?: () => void;
  maxUploadSizeMB?: number;
  uploadSuccessMessage?: string;
  onPreview?: (id: string) => void;
  previewReportIds?: string[];
};

/** The parent owns API calls and report status updates. Search filters the supplied reports. */
export default function ReportSection({ reports, selectedReportIds, onSelectionChange, onUpload, onDelete, loading = false, error, onRetry, maxUploadSizeMB, uploadSuccessMessage, onPreview, previewReportIds }: ReportSectionProps) {
  const headingId = useId();
  const [query, setQuery] = useState("");
  const [deleting, setDeleting] = useState<string[]>([]);
  const pendingDeletes = useRef(new Set<string>());
  const [deleteError, setDeleteError] = useState("");
  const terms = query.trim().toLowerCase().split(/\s+/).filter(Boolean);
  const visibleReports = reports.filter(report => {
    const text = `${report.company} ${report.year} ${report.filename} ${report.reportType ?? "Annual report"}`.toLowerCase();
    return terms.every(term => text.includes(term));
  });

  function toggleReport(id: string) {
    if (selectedReportIds.includes(id)) onSelectionChange(selectedReportIds.filter(selected => selected !== id));
    else if (reports.find(report => report.id === id)?.status === "ready") onSelectionChange([...selectedReportIds, id]);
  }

  async function deleteReport(id: string) {
    if (!onDelete || pendingDeletes.current.has(id)) return;
    pendingDeletes.current.add(id);
    setDeleting([...pendingDeletes.current]);
    setDeleteError("");
    try {
      await onDelete(id);
    } catch {
      setDeleteError("Couldn’t delete the report. Please try again.");
    } finally {
      pendingDeletes.current.delete(id);
      setDeleting([...pendingDeletes.current]);
    }
  }

  return (
    <section aria-labelledby={headingId} className="flex min-w-0 flex-col gap-4">
      <UploadReportButton onUpload={onUpload} maxSizeMB={maxUploadSizeMB} successMessage={uploadSuccessMessage} />
      <div className="mt-2 flex items-center justify-between gap-2">
        <h2 id={headingId} className="text-xs font-medium tracking-widest text-[#757a6d] uppercase dark:text-[#adb5a1]">Available reports</h2>
        {!loading && !error && <span className="text-xs text-[#757a6d] dark:text-[#adb5a1]">{visibleReports.length}</span>}
      </div>
      <SearchInput label="Search reports" placeholder="Company, year, or filename" value={query} onChange={event => setQuery(event.target.value)} />
      {deleteError && <p role="alert" className="text-xs text-red-700 dark:text-red-300">{deleteError}</p>}
      <ReportList onPreview={onPreview} previewReportIds={previewReportIds} reports={visibleReports} selectedReportIds={selectedReportIds} onSelect={toggleReport} onDelete={onDelete ? deleteReport : undefined} deletingReportIds={deleting} loading={loading} error={error} onRetry={onRetry} hasSearch={terms.length > 0} />
    </section>
  );
}
