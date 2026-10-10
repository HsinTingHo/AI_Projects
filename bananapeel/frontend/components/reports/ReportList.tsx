import Button from "../ui/Button";
import EmptyState from "../ui/EmptyState";
import ReportItem, { type Report } from "./ReportItem";

export type ReportListProps = {
  reports: Report[];
  selectedReportIds: string[];
  onSelect: (id: string) => void;
  onDelete?: (id: string) => void;
  deletingReportIds?: string[];
  loading?: boolean;
  error?: string;
  onRetry?: () => void;
  hasSearch?: boolean;
  onPreview?: (id: string) => void;
  previewReportIds?: string[];
};

export default function ReportList({ reports, selectedReportIds, onSelect, onDelete, deletingReportIds = [], loading = false, error, onRetry, hasSearch = false, onPreview, previewReportIds = [] }: ReportListProps) {
  if (loading) return <p role="status" className="px-2 py-6 text-sm text-[#757a6d] dark:text-[#adb5a1]">Loading reports…</p>;
  if (error) return <div role="alert"><EmptyState title="Couldn’t load reports" description={error} action={onRetry && <Button variant="secondary" onClick={onRetry}>Try again</Button>} /></div>;
  if (!reports.length) return <EmptyState title={hasSearch ? "No matching reports" : "Your insights start here"} description={hasSearch ? "Try another company, year, or filename." : "Upload a financial report to start exploring."} />;

  return (
    <ul aria-label="Available reports" className="flex list-none flex-col gap-2 p-0">
      {reports.map(report => <li key={report.id}><ReportItem report={report} selected={selectedReportIds.includes(report.id)} onSelect={onSelect} onDelete={onDelete} onPreview={previewReportIds.includes(report.id) ? onPreview : undefined} deleting={deletingReportIds.includes(report.id)} /></li>)}
    </ul>
  );
}
