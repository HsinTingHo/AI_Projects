export type BrandProps = { showTagline?: boolean; className?: string };

export default function Brand({ showTagline = true, className = "" }: BrandProps) {
  return (
    <div className={className}>
      <div className="flex items-center gap-2.5 text-2xl font-semibold tracking-tight text-ink dark:text-ink-dark">
        <span aria-hidden="true" className="inline-flex size-10 shrink-0 items-center justify-center rounded-xl bg-banana text-2xl">🍌</span>
        <span>BananaPeel<span className="text-muted dark:text-muted-dark">.</span></span>
      </div>
      {showTagline && <p className="mt-2 text-xs text-muted dark:text-muted-dark">A little curiosity. A lot of clarity.</p>}
    </div>
  );
}
