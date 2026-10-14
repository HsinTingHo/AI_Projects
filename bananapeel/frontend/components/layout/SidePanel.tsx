import type { ReactNode } from "react";
import Brand from "./Brand";
import ReportSection, { type ReportSectionProps } from "../reports/ReportSection";

export type SidePanelProps = ReportSectionProps & { footer?: ReactNode; className?: string };

export default function SidePanel({ footer, className = "", ...reportProps }: SidePanelProps) {
  return (
    <aside aria-label="Report library" className={`flex w-full min-w-0 flex-col gap-7 border-b border-line bg-surface-muted p-5 md:w-72 md:shrink-0 md:border-r md:border-b-0 dark:border-line-dark dark:bg-canvas-dark ${className}`}>
      <Brand />
      <ReportSection {...reportProps} />
      {footer && <div className="mt-auto border-t border-line pt-4 dark:border-line-dark">{footer}</div>}
    </aside>
  );
}
