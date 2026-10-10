"use client";

import { useEffect, useRef, useState } from "react";
import SidePanel from "./layout/SidePanel";
import Header from "./layout/Header";
import Brand from "./layout/Brand";
import Button from "./ui/Button";
import MessageList, { type ChatMessage } from "./chat/MessageList";
import ChatComposer from "./chat/ChatComposer";
import SuggestedQuestions from "./chat/SuggestedQuestions";
import type { Report } from "./reports/ReportItem";

const initialReports: Report[] = [2025, 2024].map(year => ({
  id: `sample-${year}`, company: "American Express", year,
  filename: `american-express-${year}.pdf`, status: "ready", reportType: "Sample annual report",
}));

export default function BananaPeelApp() {
  const [reports, setReports] = useState(initialReports);
  const [selected, setSelected] = useState(initialReports.map(report => report.id));
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [sending, setSending] = useState(false);
  const [libraryOpen, setLibraryOpen] = useState(false);
  const [chatVersion, setChatVersion] = useState(0);
  const [notice, setNotice] = useState("");
  const [deleteId, setDeleteId] = useState<string | null>(null);
  const [preview, setPreview] = useState<{ name: string; url: string } | null>(null);
  const files = useRef(new Map<string, { name: string; url: string }>());
  const cancellation = useRef<(() => void) | null>(null);
  const busy = useRef(false);
  const end = useRef<HTMLDivElement>(null);
  const deleteDialog = useRef<HTMLDialogElement>(null);
  const previewDialog = useRef<HTMLDialogElement>(null);
  const activeReports = reports.filter(report => selected.includes(report.id) && report.status === "ready");
  const companies = [...new Set(activeReports.map(report => report.company))];

  useEffect(() => {
    const localFiles = files.current;
    return () => { cancellation.current?.(); localFiles.forEach(file => URL.revokeObjectURL(file.url)); };
  }, []);
  useEffect(() => {
    if (messages.length) end.current?.scrollIntoView({ behavior: "instant", block: "end" });
  }, [messages]);
  useEffect(() => { if (deleteId) deleteDialog.current?.showModal(); }, [deleteId]);
  useEffect(() => { if (preview) previewDialog.current?.showModal(); }, [preview]);

  async function send(question: string) {
    if (busy.current || !activeReports.length) return;
    busy.current = true;
    setSending(true);
    setLibraryOpen(false);
    const id = crypto.randomUUID();
    setMessages(previous => [...previous, { id: `${id}-user`, role: "user", content: question }, { id, role: "assistant", content: "", status: "streaming" }]);
    let stopped = false;
    await new Promise<void>(resolve => {
      const timer = setTimeout(resolve, 800);
      cancellation.current = () => { stopped = true; clearTimeout(timer); resolve(); };
    });
    cancellation.current = null;
    const comparison = /compar|last year|2024/i.test(question);
    const risks = /risk/i.test(question);
    const headline = comparison ? "A side-by-side view of performance" : risks ? "The risks behind the numbers" : "The story behind the numbers";
    const detail = comparison
      ? "An answer would compare revenue, profitability, and cash flow across your selected periods, keeping reporting definitions and units consistent."
      : risks ? "An answer would identify the risks described in the report, explain their possible impact, and point to management’s supporting disclosures."
      : "An answer would explain the relevant results, identify the drivers behind changes, and distinguish reported figures from interpretation.";
    setMessages(previous => previous.map(message => message.id === id ? {
      id, role: "assistant", status: "complete",
      content: stopped ? "Response stopped." : `${headline}\n\n${detail}\n\nDemo answer only. No financial reports have been analyzed. Connect the Python backend to receive answers grounded in your documents.`,
      citations: stopped ? [] : [{ id: `${id}-source`, reportId: activeReports[0].id, reportTitle: "Example citation · not a report excerpt", page: 1, passage: "This is a sample source preview. In the connected app, the exact supporting passage and its PDF page appear here." }],
    } : message));
    busy.current = false;
    setSending(false);
  }

  async function upload(file: File) {
    const id = crypto.randomUUID();
    files.current.set(id, { name: file.name, url: URL.createObjectURL(file) });
    setReports(previous => [{ id, company: file.name.replace(/\.pdf$/i, ""), year: new Date().getFullYear(), filename: file.name, status: "failed", reportType: "Local PDF", error: "Preview only. Analysis is not connected." }, ...previous]);
    setNotice(`${file.name} added locally. It has not been uploaded or analyzed.`);
  }

  function removeReport() {
    if (!deleteId) return;
    const file = files.current.get(deleteId);
    if (file) URL.revokeObjectURL(file.url);
    files.current.delete(deleteId);
    setReports(previous => previous.filter(report => report.id !== deleteId));
    setSelected(previous => previous.filter(id => id !== deleteId));
    deleteDialog.current?.close();
    setDeleteId(null);
  }

  function newChat() {
    setMessages([]);
    setChatVersion(value => value + 1);
    setNotice("");
  }

  const footer = <div className="space-y-3 text-xs text-[#757a6d] dark:text-[#adb5a1]">
    <p>Good questions start here.</p>
    <div className="flex items-center gap-2"><span className="flex size-8 items-center justify-center rounded-full bg-[#fffefa] text-[#293323] dark:bg-[#303529] dark:text-[#eef1e5]" aria-hidden="true">B</span><span>My workspace<span className="block text-[11px]">Demo · This session only</span></span></div>
  </div>;

  return (
    <div className="flex min-h-dvh flex-col bg-[#fffefa] text-[#293323] md:flex-row dark:bg-[#1c1e18] dark:text-[#eef1e5]">
      <a href="#main-content" className="sr-only z-50 rounded-lg bg-[#f5d84b] p-3 text-[#293323] focus:not-sr-only focus:absolute">Skip to chat</a>
      <div className="flex items-center justify-between gap-2 border-b border-[#e5e6db] p-4 md:hidden dark:border-[#3c4234]">
        <Brand showTagline={false} />
        <Button variant="secondary" aria-expanded={libraryOpen} aria-controls="report-library" onClick={() => setLibraryOpen(open => !open)}>{libraryOpen ? "Close" : "Reports"}</Button>
      </div>
      <div id="report-library" className={`${libraryOpen ? "flex" : "hidden"} md:flex`}>
        <SidePanel className="h-full" reports={reports} selectedReportIds={selected} onSelectionChange={setSelected} onUpload={upload} onDelete={async id => setDeleteId(id)} uploadSuccessMessage="PDF added locally. No file was sent to a server." footer={footer} onPreview={id => { const file = files.current.get(id); if (file) setPreview(file); }} previewReportIds={reports.filter(report => !report.id.startsWith("sample-")).map(report => report.id)} />
      </div>
      <main id="main-content" className="flex min-w-0 flex-1 flex-col">
        <Header context={companies.length === 1 ? companies[0] : companies.length ? `${companies.length} companies` : "Your workspace"} onNewChat={newChat} disabled={sending} />
        <div className="flex flex-wrap items-center justify-between gap-2 border-b border-[#e5e6db] bg-[#fbf6dd] px-5 py-2.5 text-xs text-[#62551b] dark:border-[#3c4234] dark:bg-[#302d1d] dark:text-[#ddd09c]"><span><strong className="font-medium">Demo workspace</strong> · Sample answers. Files stay in this tab.</span><span>Python backend not connected</span></div>
        {notice && <div role="status" className="flex items-start justify-between gap-3 px-5 pt-4 text-xs text-[#757a6d] dark:text-[#adb5a1]"><p className="break-all">{notice}</p><button type="button" aria-label="Dismiss notification" onClick={() => setNotice("")} className="rounded p-1">✕</button></div>}
        <div className="mx-auto flex w-full max-w-4xl flex-1 flex-col px-5 sm:px-10 lg:px-16">
          <div className={`flex-1 py-10 ${messages.length ? "" : "flex flex-col justify-center"}`}>
            <MessageList messages={messages} emptyState={<section className="mx-auto w-full max-w-xl py-4 sm:py-10">
              <div className="mb-9 text-center">
                <span aria-hidden="true" className="mb-7 inline-flex size-20 -rotate-9 items-center justify-center rounded-3xl bg-[#fbf1b9] text-5xl dark:bg-[#474122]">🍌</span>
                <p className="mb-3 text-xs font-medium tracking-[0.18em] text-[#757a6d] uppercase dark:text-[#adb5a1]">A fresh take on financials</p>
                <h2 className="font-serif text-5xl tracking-tight sm:text-6xl">Go Bananas.</h2>
                <p className="mt-5 text-base leading-7 text-[#757a6d] dark:text-[#adb5a1]">Peel back the numbers.<br />Find the story inside your company’s financials.</p>
              </div>
              <SuggestedQuestions questions={["What drove revenue in 2025?", "Compare 2025 with 2024", "Give me the key takeaways", "What risks should I watch?"]} onSelect={question => void send(question)} disabled={!activeReports.length || sending} />
              {!activeReports.length && <p className="mt-4 text-center text-xs text-[#757a6d] dark:text-[#adb5a1]">Select a sample report in the library to explore the demo.</p>}
            </section>} />
            <div ref={end} />
          </div>
          <div className="bg-[#fffefa] pb-5 pt-3 md:sticky md:bottom-0 dark:bg-[#1c1e18]"><ChatComposer key={chatVersion} onSend={send} selectedReportCount={activeReports.length} isSending={sending} onStop={() => cancellation.current?.()} /></div>
        </div>
      </main>
      <dialog ref={deleteDialog} onCancel={() => setDeleteId(null)} onClose={() => setDeleteId(null)} aria-labelledby="delete-heading" className="m-auto w-[calc(100%-2rem)] max-w-sm rounded-2xl bg-[#fffefa] p-6 text-[#293323] backdrop:bg-black/40 dark:bg-[#24271f] dark:text-[#eef1e5]">
        <h2 id="delete-heading" className="text-lg font-medium">Remove this report?</h2><p className="mt-2 break-words text-sm text-[#757a6d] dark:text-[#adb5a1]">{reports.find(report => report.id === deleteId)?.filename} will be removed from this workspace.</p>
        <div className="mt-6 flex justify-end gap-2"><Button variant="ghost" onClick={() => deleteDialog.current?.close()}>Cancel</Button><Button onClick={removeReport}>Remove report</Button></div>
      </dialog>
      <dialog ref={previewDialog} onClose={() => setPreview(null)} aria-labelledby="preview-heading" className="m-auto w-[calc(100%-2rem)] max-w-4xl rounded-2xl bg-[#fffefa] p-5 text-[#293323] backdrop:bg-black/40 dark:bg-[#24271f] dark:text-[#eef1e5]">
        <div className="mb-4 flex items-center justify-between gap-3"><h2 id="preview-heading" className="min-w-0 break-all text-sm font-medium">{preview?.name}</h2><Button variant="ghost" onClick={() => previewDialog.current?.close()}>Close</Button></div>
        {preview && <><p className="mb-3 text-xs">Local preview only · Not analyzed</p><object data={preview.url} type="application/pdf" className="h-[65dvh] w-full"><p>Preview unavailable. <a href={preview.url} target="_blank" rel="noopener noreferrer" className="underline">Open PDF in a new tab</a></p></object></>}
      </dialog>
    </div>
  );
}
