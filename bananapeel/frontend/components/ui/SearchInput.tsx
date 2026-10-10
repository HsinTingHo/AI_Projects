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
        className={hideLabel ? "sr-only" : "mb-2 block text-sm font-medium text-[#293323] dark:text-[#eef1e5]"}
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
          className="pointer-events-none absolute top-1/2 left-3 size-4 -translate-y-1/2 text-[#757a6d] dark:text-[#adb5a1]"
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
            "min-h-11 w-full min-w-0 rounded-xl border border-[#e5e6db] bg-[#fffefa] py-2.5 pr-3 pl-9 text-base text-[#293323] sm:text-sm",
            "placeholder:text-[#757a6d] dark:border-[#3c4234] dark:bg-[#24271f] dark:text-[#eef1e5] dark:placeholder:text-[#adb5a1]",
            "focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[#827013] dark:focus-visible:outline-[#f5d84b]",
            "disabled:cursor-not-allowed disabled:opacity-50",
            className,
          ].join(" ")}
        />
      </div>
    </div>
  );
}
