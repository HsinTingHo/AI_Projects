"use client";

import { useId, type ComponentPropsWithRef } from "react";

export type SearchInputProps = Omit<ComponentPropsWithRef<"input">, "type"> & {
  label: string;
  hideLabel?: boolean;
  containerClassName?: string;
};

export default function SearchInput({
  label,
  hideLabel = false,
  containerClassName = "",
  className = "",
  id,
  placeholder = "Search…",
  disabled,
  ...props
}: SearchInputProps) {
  const generatedId = useId();
  const inputId = id ?? generatedId;

  return (
    <div className={`min-w-0 ${containerClassName}`}>
      <label
        htmlFor={inputId}
        className={hideLabel ? "sr-only" : "mb-2 block text-sm font-medium text-ink dark:text-ink-dark"}
      >
        {label}
      </label>
      <div className="relative">
        <svg
          aria-hidden="true"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="1.75"
          strokeLinecap="round"
          className="pointer-events-none absolute top-1/2 left-3 size-4 -translate-y-1/2 text-muted dark:text-muted-dark"
        >
          <circle cx="10.5" cy="10.5" r="6.5" />
          <path d="m16 16 4.5 4.5" />
        </svg>
        <input
          {...props}
          id={inputId}
          type="search"
          disabled={disabled}
          placeholder={placeholder}
          className={[
            "min-h-11 w-full min-w-0 rounded-xl border border-line bg-surface py-2.5 pr-3 pl-9 text-base text-ink sm:text-sm",
            "placeholder:text-muted dark:border-line-dark dark:bg-surface-dark dark:text-ink-dark dark:placeholder:text-muted-dark",
            "focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-olive dark:focus-visible:outline-banana",
            "disabled:cursor-not-allowed disabled:opacity-50",
            className,
          ].join(" ")}
        />
      </div>
    </div>
  );
}
