import Button from "../ui/Button";

export type SuggestedQuestionsProps = {
  questions?: readonly string[];
  onSelect: (question: string) => void;
  disabled?: boolean;
};

const defaults = [
  "What drove revenue growth?",
  "Compare performance across these reports",
  "Give me the key takeaways",
  "What risks should I watch?",
];

export default function SuggestedQuestions({ questions = defaults, onSelect, disabled = false }: SuggestedQuestionsProps) {
  if (!questions.length) return null;
  return (
    <ul aria-label="Suggested questions" className="grid list-none grid-cols-1 gap-3 p-0 sm:grid-cols-2">
      {questions.map((question, index) => (
        <li key={`${index}-${question}`} className="flex">
          <Button variant="secondary" fullWidth disabled={disabled} onClick={() => onSelect(question)} className="h-full text-left">
            <span className="min-w-0 flex-1 break-words">{question}</span>
            <span aria-hidden="true">↗</span>
          </Button>
        </li>
      ))}
    </ul>
  );
}
