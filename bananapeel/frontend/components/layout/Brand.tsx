export type BrandProps = { showTagline?: boolean; className?: string };

export default function Brand({ showTagline = true, className = "" }: BrandProps) {
  return (
    <div className={className}>
      <div className="flex items-center gap-2.5 text-2xl font-semibold tracking-tight text-[#293323] dark:text-[#eef1e5]">
        <span aria-hidden="true" className="inline-flex size-10 shrink-0 items-center justify-center rounded-xl bg-[#f5d84b] text-2xl">🍌</span>
        <span>BananaPeel<span className="text-[#757a6d] dark:text-[#adb5a1]">.</span></span>
      </div>
      {showTagline && <p className="mt-2 text-xs text-[#757a6d] dark:text-[#adb5a1]">A little curiosity. A lot of clarity.</p>}
    </div>
  );
}
