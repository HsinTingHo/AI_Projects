import IconButton from "../ui/IconButton";
import StatusBadge, { type StatusBadgeProps } from "../ui/StatusBadge";

export type Report = {
  id: string;
  company: string;
  year: number;
  filename: string;
  status: StatusBadgeProps["status"];
  reportType?: string;
  error?: string;
};

export type ReportItemProps = {
  report: Report;
  selected: boolean;
  onSelect: (id: string) => void;
  onDelete?: (id: string) => void;
  deleting?: boolean;
  onPreview?: (id: string) => void;
};

export default function ReportItem({ report, selected, onSelect, onDelete, onPreview, deleting = false }: ReportItemProps) {
  const label = `${report.company} ${report.year} ${report.reportType ?? "Annual report"}`;

  return (
    <div className={`flex items-start gap-1 rounded-xl border p-2 ${selected ? "border-[#d3c566] bg-[#fffefa] dark:border-[#827013] dark:bg-[#24271f]" : "border-transparent"}`}>
      <button
        type="button"
        aria-label={`${selected ? "Deselect" : "Select"} ${label}`}
        aria-pressed={selected}
        disabled={deleting || (!selected && report.status !== "ready")}
        onClick={() => onSelect(report.id)}
        className="flex min-h-11 min-w-0 flex-1 items-start gap-2 rounded-lg p-1 text-left text-[#293323] focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[#827013] disabled:cursor-not-allowed dark:text-[#eef1e5] dark:focus-visible:outline-[#f5d84b]"
      >
        <span aria-hidden="true" className="mt-0.5 text-sm">{selected ? "☑" : "☐"}</span>
        <span className="flex min-w-0 flex-col items-start gap-1.5">
          <span className="break-words text-sm font-medium">{report.company}</span>
          <span className="text-xs text-[#757a6d] dark:text-[#adb5a1]">{report.year} · {report.reportType ?? "Annual report"}</span>
          <StatusBadge status={report.status} role={undefined} />
          {report.status === "failed" && report.error && <span className="break-words text-xs text-red-700 dark:text-red-300">{report.error}</span>}
        </span>
      </button>
      {onPreview && <IconButton label={`Preview ${label}`} onClick={() => onPreview(report.id)}><span>↗</span></IconButton>}
      {onDelete && (
        <IconButton label={`Delete ${label}`} loading={deleting} onClick={() => onDelete(report.id)}>
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"><path d="M3 6h18M9 6V3h6v3M5 6l1 15h12l1-15M10 10v7M14 10v7" /></svg>
        </IconButton>
      )}
    </div>
  );
}
