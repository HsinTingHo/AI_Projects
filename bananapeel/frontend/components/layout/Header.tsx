import Button from "../ui/Button";

export type HeaderProps = {
  title?: string;
  context?: string;
  onNewChat: () => void;
  disabled?: boolean;
};

export default function Header({ title = "Report insights", context, onNewChat, disabled = false }: HeaderProps) {
  return (
    <header className="flex flex-wrap items-center justify-between gap-3 border-b border-[#e5e6db] bg-[#fffefa] px-5 py-4 dark:border-[#3c4234] dark:bg-[#1c1e18]">
      <div className="flex min-w-0 flex-wrap items-baseline gap-2">
        <h1 className="text-sm font-medium text-[#293323] dark:text-[#eef1e5]">{title}</h1>
        {context && <span className="text-xs text-[#757a6d] [overflow-wrap:anywhere] dark:text-[#adb5a1]">/ {context}</span>}
      </div>
      <Button variant="ghost" onClick={onNewChat} disabled={disabled}><span aria-hidden="true">＋</span>New chat</Button>
    </header>
  );
}
