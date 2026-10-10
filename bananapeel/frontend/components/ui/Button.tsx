import type { ComponentPropsWithRef } from "react";

const variants = {
  primary:
    "bg-[#f5d84b] text-[#293323] enabled:hover:bg-[#e8ca39]",
  secondary:
    "border border-[#e5e6db] bg-[#fffefa] text-[#293323] enabled:hover:bg-[#f5f4ec] dark:border-[#3c4234] dark:bg-[#24271f] dark:text-[#eef1e5] dark:enabled:hover:bg-[#303529]",
  ghost:
    "bg-transparent text-[#293323] enabled:hover:bg-[#f5f4ec] dark:text-[#eef1e5] dark:enabled:hover:bg-[#303529]",
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
        "focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[#827013] dark:focus-visible:outline-[#f5d84b]",
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
