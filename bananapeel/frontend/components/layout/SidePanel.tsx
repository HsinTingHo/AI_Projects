import type { ReactNode } from "react";
import Brand from "./Brand";
import ReportSection, { type ReportSectionProps } from "../reports/ReportSection";

export type SidePanelProps = ReportSectionProps & { footer?: ReactNode; className?: string };

export default function SidePanel({ footer, className = "", ...reportProps }: SidePanelProps) {
  return (
    <aside aria-label="Report library" className={`flex w-full min-w-0 flex-col gap-7 border-b border-[#e5e6db] bg-[#f5f4ec] p-5 md:w-72 md:shrink-0 md:border-r md:border-b-0 dark:border-[#3c4234] dark:bg-[#1c1e18] ${className}`}>
      <Brand />
      <ReportSection {...reportProps} />
      {footer && <div className="mt-auto border-t border-[#e5e6db] pt-4 dark:border-[#3c4234]">{footer}</div>}
    </aside>
  );
}
