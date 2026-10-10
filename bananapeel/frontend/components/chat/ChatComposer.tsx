"use client";

import { useId, useRef, useState, type FormEvent } from "react";
import Button from "../ui/Button";
import IconButton from "../ui/IconButton";

export type ChatComposerProps = {
  /** Reject on failure to retain the draft. Parent owns message history and streaming. */
  onSend: (message: string) => Promise<void>;
  selectedReportCount: number;
  isSending?: boolean;
  disabled?: boolean;
  onStop?: () => void;
  maxLength?: number;
};

export default function ChatComposer({ onSend, selectedReportCount, isSending = false, disabled = false, onStop, maxLength = 4000 }: ChatComposerProps) {
  const id = useId();
  const [draft, setDraft] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");
  const lock = useRef(false);
  const busy = submitting || isSending;
  const blocked = disabled || busy || selectedReportCount < 1;

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const message = draft.trim();
    if (!message || blocked || lock.current) return;
    lock.current = true;
    setSubmitting(true);
    setError("");
    try {
      await onSend(message);
      setDraft("");
    } catch {
      setError("Couldn’t send your question. Your draft is saved here—try again.");
    } finally {
      lock.current = false;
      setSubmitting(false);
    }
  }

  return (
    <div className="space-y-2">
      <form onSubmit={submit} aria-label="Ask about your reports" className="rounded-2xl border border-[#e5e6db] bg-[#fffefa] p-4 dark:border-[#3c4234] dark:bg-[#24271f]">
        <label htmlFor={id} className="sr-only">Your question</label>
        <textarea id={id} value={draft} onChange={event => setDraft(event.target.value)} disabled={disabled} readOnly={busy} maxLength={maxLength} rows={2} aria-describedby={`${id}-context${error ? ` ${id}-error` : ""}`} placeholder="Ask a question. Find the insight." onKeyDown={event => {
          if (event.key === "Enter" && !event.shiftKey && !event.nativeEvent.isComposing && event.nativeEvent.keyCode !== 229) {
            event.preventDefault();
            event.currentTarget.form?.requestSubmit();
          }
        }} className="min-h-16 w-full resize-y rounded-md bg-transparent text-base text-[#293323] outline-offset-4 placeholder:text-[#757a6d] disabled:opacity-50 dark:text-[#eef1e5] dark:placeholder:text-[#adb5a1]" />
        <div className="mt-2 flex flex-wrap items-center justify-between gap-2">
          <p id={`${id}-context`} className="text-xs text-[#757a6d] dark:text-[#adb5a1]">{selectedReportCount > 0 ? `${selectedReportCount} report${selectedReportCount === 1 ? "" : "s"} selected` : "Select a ready report to ask a question."}</p>
          {busy && onStop ? <Button variant="secondary" onClick={onStop}>Stop</Button> : <IconButton label={busy ? "Sending question" : "Send question"} type="submit" variant="primary" disabled={blocked || !draft.trim()} loading={busy}><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M12 19V5m-6 6 6-6 6 6" /></svg></IconButton>}
        </div>
      </form>
      {error && <p id={`${id}-error`} role="alert" className="text-sm text-red-700 dark:text-red-300">{error}</p>}
      <p className="text-center text-xs text-[#757a6d] dark:text-[#adb5a1]">Rooted in your reports. Linked to the source.</p>
    </div>
  );
}
