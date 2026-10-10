import Button, { type ButtonProps } from "./Button";

export type IconButtonProps = Omit<
  ButtonProps,
  "aria-label" | "children" | "fullWidth" | "loadingText"
> & {
  label: string;
  children: React.ReactNode;
};

const widths = { sm: 36, md: 44, lg: 48 } as const;

export default function IconButton({
  label,
  children,
  size = "md",
  variant = "ghost",
  loading = false,
  style,
  ...props
}: IconButtonProps) {
  return (
    <Button
      {...props}
      aria-label={label}
      size={size}
      variant={variant}
      loading={loading}
      style={{ width: widths[size], padding: 0, flexShrink: 0, ...style }}
    >
      {!loading && (
        <span aria-hidden="true" className="inline-flex items-center justify-center [&>svg]:size-5">
          {children}
        </span>
      )}
    </Button>
  );
}
