export type Citation = {
  id: string;
  reportId: string;
  reportTitle: string;
  /** One-based PDF page number. */
  page: number;
  passage: string;
  /** An authorized PDF endpoint or signed URL supplied by the backend. */
  fileUrl?: string;
};

export type SourceCitationProps = { citation: Citation };

function pageLink(fileUrl: string | undefined, page: number) {
  if (!fileUrl || !Number.isInteger(page) || page < 1) return undefined;
  // Allow same-origin paths and HTTP(S), never executable URL schemes.
  const value = fileUrl.trim();
  if (!/^(https?:\/\/|\/(?!\/))/i.test(value) || /[\\\s]/.test(value)) return undefined;
  return `${value.split("#")[0]}#page=${page}`;
}

export default function SourceCitation({ citation }: SourceCitationProps) {
  const href = pageLink(citation.fileUrl, citation.page);
  return (
    <details className="min-w-0 rounded-xl border border-[#e5e6db] bg-[#fffefa] text-sm dark:border-[#3c4234] dark:bg-[#24271f]">
      <summary className="cursor-pointer rounded-xl px-3 py-2 text-[#293323] focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[#827013] dark:text-[#eef1e5] dark:focus-visible:outline-[#f5d84b]">
        <span className="[overflow-wrap:anywhere]">{citation.reportTitle} · p. {citation.page}</span>
      </summary>
      <div className="space-y-3 border-t border-[#e5e6db] p-3 dark:border-[#3c4234]">
        <blockquote className="whitespace-pre-wrap text-sm leading-relaxed text-[#757a6d] [overflow-wrap:anywhere] dark:text-[#adb5a1]">{citation.passage}</blockquote>
        {href && <a href={href} target="_blank" rel="noopener noreferrer" className="inline-block py-2 font-medium text-[#62551b] underline underline-offset-4 dark:text-[#f5d84b]">Open PDF at page {citation.page}<span className="sr-only"> (opens in a new tab)</span></a>}
      </div>
    </details>
  );
}
