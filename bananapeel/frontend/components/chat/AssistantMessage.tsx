import Button from "../ui/Button";
import SourceCitation, { type Citation } from "./SourceCitation";

export type AssistantMessageProps = {
  content: string;
  citations?: Citation[];
  status?: "streaming" | "complete" | "error";
  error?: string;
  onRetry?: () => void;
};

export default function AssistantMessage({ content, citations = [], status = "complete", error, onRetry }: AssistantMessageProps) {
  return (
    <article aria-label="BananaPeel answer" aria-busy={status === "streaming"} className="min-w-0 space-y-4 text-[#293323] dark:text-[#eef1e5]">
      <div className="flex items-center gap-2 text-sm font-medium"><span aria-hidden="true" className="inline-flex size-8 items-center justify-center rounded-lg bg-[#f5d84b]">🍌</span>BananaPeel</div>
      {content && <div className="whitespace-pre-wrap text-sm leading-7 [overflow-wrap:anywhere]">{content}</div>}
      {status === "streaming" && <p role="status" className="text-xs text-[#757a6d] dark:text-[#adb5a1]">{content ? "Writing answer…" : "Looking through your reports…"}</p>}
      {status === "error" && <div className="space-y-2"><p role="alert" className="text-sm text-red-700 dark:text-red-300">{error || "Couldn’t finish this answer. Please try again."}</p>{onRetry && <Button variant="secondary" onClick={onRetry}>Try again</Button>}</div>}
      {citations.length > 0 && <div className="space-y-2"><p className="text-xs font-medium text-[#757a6d] dark:text-[#adb5a1]">Sources</p><ul aria-label="Answer sources" className="list-none space-y-2 p-0">{citations.map(citation => <li key={citation.id}><SourceCitation citation={citation} /></li>)}</ul></div>}
    </article>
  );
}
