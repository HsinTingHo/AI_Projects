export type UserMessageProps = { content: string };

export default function UserMessage({ content }: UserMessageProps) {
  return (
    <article aria-label="Your message" className="ml-auto w-fit max-w-[90%] rounded-2xl rounded-br-sm bg-[#f5f4ec] px-4 py-3 text-sm leading-relaxed text-[#293323] dark:bg-[#24271f] dark:text-[#eef1e5]">
      <p className="whitespace-pre-wrap [overflow-wrap:anywhere]">{content}</p>
    </article>
  );
}
