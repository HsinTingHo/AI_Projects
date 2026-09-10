import json
import random
from pathlib import Path

def shuffle_jsonl(input_path: str | Path, output_path: str | Path) -> None:
    input_path = Path(input_path)
    output_path = Path(output_path)

    with input_path.open("r", encoding="utf-8") as infile:
        records = [json.loads(line) for line in infile if line.strip()]

    random.shuffle(records)

    with output_path.open("w", encoding="utf-8") as outfile:
        for record in records:
            outfile.write(json.dumps(record, ensure_ascii=False) + "\n")

    print(f"Shuffled {len(records)} records from {input_path} -> {output_path}")

if __name__ == "__main__":
    shuffle_jsonl(
        "/Users/eva/Desktop/Projects/AI_Project/resources/evaluations/eval_amex_2025_dev_v1.jsonl",
        "/Users/eva/Desktop/Projects/AI_Project/resources/evaluations/eval_amex_2025_dev_v1_shuffled.jsonl",
    )