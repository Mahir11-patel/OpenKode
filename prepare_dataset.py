"""Extract a small local training sample from the Open-Kode knowledge base."""
from __future__ import annotations

import argparse
import json
import random
import re
from pathlib import Path

try:
    import ijson
except ImportError as exc:
    raise SystemExit("Install training dependencies with: python -m pip install -r training/requirements.txt") from exc


RECORD_FIELD = re.compile(r"^facts\.(qa_[^.]+)\.(question|answer)$")
DEFAULT_SOURCE = Path(__file__).resolve().parents[2] / "data" / "knowledge_base.json"
DEFAULT_OUTPUT = Path(__file__).resolve().parent / "data" / "openkode_train.jsonl"


def extract_sample(source: Path, output: Path, max_samples: int, seed: int) -> tuple[int, int, bool]:
    randomizer = random.Random(seed)
    reservoir: list[tuple[str, str]] = []
    pending: dict[str, dict[str, str]] = {}
    seen = 0
    malformed = False

    with source.open("rb") as handle:
        try:
            for prefix, event, value in ijson.parse(handle):
                match = RECORD_FIELD.match(prefix)
                if not match or event != "string":
                    continue
                record_id, field = match.groups()
                record = pending.setdefault(record_id, {})
                record[field] = value.strip()
                if "question" not in record or "answer" not in record:
                    continue
                question, answer = record["question"], record["answer"]
                pending.pop(record_id, None)
                if not question or not answer or len(question) > 500 or len(answer) > 20000:
                    continue
                seen += 1
                sample = (question, answer)
                if len(reservoir) < max_samples:
                    reservoir.append(sample)
                else:
                    slot = randomizer.randrange(seen)
                    if slot < max_samples:
                        reservoir[slot] = sample
        except ijson.common.IncompleteJSONError:
            # Keep records parsed before the malformed source record. Never rewrite the original.
            malformed = True

    if not reservoir:
        raise SystemExit(f"No intact question/answer records were found in {source}.")

    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", encoding="utf-8", newline="\n") as handle:
        for question, answer in reservoir:
            row = {
                "text": f"User: {question}\nOpen-Kode: {answer}",
                "question": question,
            }
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")
    return seen, len(reservoir), malformed


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE, help="Local JSON knowledge base; it is read only.")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--max-samples", type=int, default=350)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()
    if args.max_samples < 1:
        parser.error("--max-samples must be greater than zero")
    seen, selected, malformed = extract_sample(args.source, args.output, args.max_samples, args.seed)
    state = " The source contains malformed JSON; only complete records before the error were used." if malformed else ""
    print(f"Prepared {selected} local Q&A samples from {seen} intact records at {args.output}.{state}")


if __name__ == "__main__":
    main()
