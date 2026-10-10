import type { ComponentPropsWithoutRef } from "react";

const statuses = {
  uploading: {
    label: "Uploading",
    className: "bg-blue-50 text-blue-800 dark:bg-blue-950 dark:text-blue-200",
  },
  processing: {
    label: "Processing",
    className: "bg-amber-50 text-amber-800 dark:bg-amber-950 dark:text-amber-200",
  },
  ready: {
    label: "Ready",
    className: "bg-green-50 text-green-800 dark:bg-green-950 dark:text-green-200",
  },
  failed: {
    label: "Failed",
    className: "bg-red-50 text-red-800 dark:bg-red-950 dark:text-red-200",
  },
} as const;

export type StatusBadgeProps = Omit<ComponentPropsWithoutRef<"span">, "children"> & {
  status: keyof typeof statuses;
  label?: string;
};

export default function StatusBadge({
  status,
  label,
  className = "",
  ...props
}: StatusBadgeProps) {
  const appearance = statuses[status];

  return (
    <span
      role="status"
      {...props}
      className={`inline-flex items-center gap-1.5 rounded-full px-2 py-1 text-xs font-medium ${appearance.className} ${className}`}
    >
      <span aria-hidden="true" className="size-1.5 shrink-0 rounded-full bg-current" />
      {label ?? appearance.label}
    </span>
  );
}
