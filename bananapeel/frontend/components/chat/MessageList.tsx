import type { ReactNode } from "react";
import AssistantMessage, { type AssistantMessageProps } from "./AssistantMessage";
import UserMessage from "./UserMessage";

export type ChatMessage =
  | { id: string; role: "user"; content: string }
  | ({ id: string; role: "assistant" } & Omit<AssistantMessageProps, "onRetry">);

export type MessageListProps = {
  messages: ChatMessage[];
  isLoading?: boolean;
  onRetry?: (messageId: string) => void;
  emptyState?: ReactNode;
};

export default function MessageList({ messages, isLoading = false, onRetry, emptyState }: MessageListProps) {
  if (!messages.length && !isLoading) return <>{emptyState}</>;
  const hasStreamingMessage = messages.some(message => message.role === "assistant" && message.status === "streaming");
  return (
    <div role="log" aria-label="Conversation" aria-live="polite" aria-relevant="additions" className="min-w-0">
      <ol className="list-none space-y-8 p-0">
        {messages.map(message => <li key={message.id}>{message.role === "user" ? <UserMessage content={message.content} /> : <AssistantMessage content={message.content} citations={message.citations} status={message.status} error={message.error} onRetry={onRetry ? () => onRetry(message.id) : undefined} />}</li>)}
        {isLoading && !hasStreamingMessage && <li><AssistantMessage content="" status="streaming" /></li>}
      </ol>
    </div>
  );
}
