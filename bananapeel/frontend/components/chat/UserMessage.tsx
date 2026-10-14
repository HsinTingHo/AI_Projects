export type UserMessageProps = { content: string };

export default function UserMessage({ content }: UserMessageProps) {
  return (
    <article aria-label="Your message" className="ml-auto w-fit max-w-[90%] rounded-2xl rounded-br-sm bg-surface-muted px-4 py-3 text-sm leading-relaxed text-ink dark:bg-surface-dark dark:text-ink-dark">
      <p className="whitespace-pre-wrap [overflow-wrap:anywhere]">{content}</p>
    </article>
  );
}
