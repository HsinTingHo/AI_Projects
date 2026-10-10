import type { ComponentPropsWithoutRef, ReactNode } from "react";

export type EmptyStateProps = Omit<ComponentPropsWithoutRef<"div">, "title" | "children"> & {
  title: string;
  description?: string;
  icon?: ReactNode;
  action?: ReactNode;
};

export default function EmptyState({
  title,
  description,
  icon,
  action,
  className = "",
  ...props
}: EmptyStateProps) {
  return (
    <div
      {...props}
      className={`flex flex-col items-center gap-3 px-5 py-10 text-center ${className}`}
    >
      {icon && (
        <span
          aria-hidden="true"
          className="mb-1 inline-flex size-12 items-center justify-center rounded-2xl bg-[#fbf1b9] text-[#62551b] dark:bg-[#474122] dark:text-[#f5d84b] [&>svg]:size-6"
        >
          {icon}
        </span>
      )}
      <p className="text-base font-medium text-[#293323] dark:text-[#eef1e5]">
        {title}
      </p>
      {description && (
        <p className="max-w-sm text-sm leading-relaxed text-[#757a6d] dark:text-[#adb5a1]">
          {description}
        </p>
      )}
      {action && <div className="mt-2 flex flex-wrap justify-center gap-2">{action}</div>}
    </div>
  );
}
