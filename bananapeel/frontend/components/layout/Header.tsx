import Button from "../ui/Button";

export type HeaderProps = {
  title?: string;
  context?: string;
  onNewChat: () => void;
  disabled?: boolean;
};

export default function Header({ title = "Report insights", context, onNewChat, disabled = false }: HeaderProps) {
  return (
    <header className="flex flex-wrap items-center justify-between gap-3 border-b border-line bg-surface px-5 py-4 dark:border-line-dark dark:bg-canvas-dark">
      <div className="flex min-w-0 flex-wrap items-baseline gap-2">
        <h1 className="text-sm font-medium text-ink dark:text-ink-dark">{title}</h1>
        {context && <span className="text-xs text-muted [overflow-wrap:anywhere] dark:text-muted-dark">/ {context}</span>}
      </div>
      <Button variant="ghost" onClick={onNewChat} disabled={disabled}><span aria-hidden="true">＋</span>New chat</Button>
    </header>
  );
}
