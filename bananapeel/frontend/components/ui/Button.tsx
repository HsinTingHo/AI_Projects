import type { ComponentPropsWithRef } from "react";

const variants = {
  primary:
    "bg-banana text-ink enabled:hover:bg-banana-hover",
  secondary:
    "border border-line bg-surface text-ink enabled:hover:bg-surface-muted dark:border-line-dark dark:bg-surface-dark dark:text-ink-dark dark:enabled:hover:bg-surface-hover-dark",
  ghost:
    "bg-transparent text-ink enabled:hover:bg-surface-muted dark:text-ink-dark dark:enabled:hover:bg-surface-hover-dark",
} as const;

const sizes = {
  sm: "min-h-9 px-3 py-1.5 text-sm",
  md: "min-h-11 px-4 py-2.5 text-sm",
  lg: "min-h-12 px-5 py-3 text-base",
} as const;

export type ButtonProps = ComponentPropsWithRef<"button"> & {
  variant?: keyof typeof variants;
  size?: keyof typeof sizes;
  loading?: boolean;
  loadingText?: string;
  fullWidth?: boolean;
};

/** Use inside a Client Component when passing event handlers. */
export default function Button({
  variant = "primary",
  size = "md",
  loading = false,
  loadingText,
  fullWidth = false,
  disabled = false,
  type = "button",
  className = "",
  children,
  "aria-busy": ariaBusy,
  ...props
}: ButtonProps) {
  return (
    <button
      {...props}
      type={type}
      disabled={disabled || loading}
      aria-busy={loading || ariaBusy}
      className={[
        "inline-flex items-center justify-center gap-2 rounded-xl font-medium transition-colors motion-reduce:transition-none",
        "focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-olive dark:focus-visible:outline-banana",
        "disabled:cursor-not-allowed disabled:opacity-50 enabled:cursor-pointer",
        variants[variant],
        sizes[size],
        fullWidth ? "w-full" : "",
        className,
      ]
        .filter(Boolean)
        .join(" ")}
    >
      {loading && (
        <span
          aria-hidden="true"
          className="size-4 shrink-0 animate-spin rounded-full border-2 border-current border-r-transparent motion-reduce:animate-none"
        />
      )}
      {loading && loadingText ? loadingText : children}
    </button>
  );
}
