"""Fine-tune a small pretrained language model on a local Open-Kode sample."""
from __future__ import annotations

import argparse
import json
import os
import random
import time
from pathlib import Path


TRAINING_DIR = Path(__file__).resolve().parent
DEFAULT_DATASET = TRAINING_DIR / "data" / "openkode_train.jsonl"
DEFAULT_OUTPUT = TRAINING_DIR / "output" / "openkode-distilgpt2"
DEFAULT_BASE_MODEL = "distilbert/distilgpt2"
MIN_FREE_RAM_GB = 2.0


def available_ram_gb() -> float | None:
    """Return available physical RAM without importing the ML stack."""
    try:
        if os.name == "nt":
            import ctypes
            from ctypes import wintypes

            class MemoryStatus(ctypes.Structure):
                _fields_ = [
                    ("length", wintypes.DWORD), ("memory_load", wintypes.DWORD),
                    ("total_phys", ctypes.c_ulonglong), ("available_phys", ctypes.c_ulonglong),
                    ("total_page_file", ctypes.c_ulonglong), ("available_page_file", ctypes.c_ulonglong),
                    ("total_virtual", ctypes.c_ulonglong), ("available_virtual", ctypes.c_ulonglong),
                    ("available_extended_virtual", ctypes.c_ulonglong),
                ]

            status = MemoryStatus()
            status.length = ctypes.sizeof(status)
            if ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(status)):
                return status.available_phys / (1024 ** 3)
        elif hasattr(os, "sysconf"):
            available_pages = os.sysconf("SC_AVPHYS_PAGES")
            page_size = os.sysconf("SC_PAGE_SIZE")
            return available_pages * page_size / (1024 ** 3)
    except (AttributeError, OSError, ValueError):
        return None
    return None


def load_rows(dataset_path: Path, tokenizer, max_length: int, limit: int):
    import torch

    rows = []
    with dataset_path.open("r", encoding="utf-8") as handle:
        for line in handle:
            if len(rows) >= limit:
                break
            record = json.loads(line)
            encoded = tokenizer(record["text"], truncation=True, max_length=max_length, add_special_tokens=False)
            ids = encoded["input_ids"]
            if len(ids) < 4:
                continue
            rows.append(torch.tensor(ids, dtype=torch.long))
    return rows


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", type=Path, default=DEFAULT_DATASET)
    parser.add_argument("--base-model", default=DEFAULT_BASE_MODEL)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--max-samples", type=int, default=350)
    parser.add_argument("--max-length", type=int, default=96)
    parser.add_argument("--epochs", type=int, default=1)
    args = parser.parse_args()
    if not args.dataset.is_file():
        raise SystemExit(f"Training data not found: {args.dataset}. Run training/prepare_dataset.py first.")
    if args.max_samples < 1 or args.max_length < 8 or args.epochs < 1:
        parser.error("--max-samples and --epochs must be positive; --max-length must be at least 8")

    free_ram = available_ram_gb()
    if free_ram is not None and free_ram < MIN_FREE_RAM_GB:
        raise SystemExit(
            f"Training stopped before loading PyTorch: only {free_ram:.2f} GB RAM is free; "
            f"close memory-heavy applications and retry with at least {MIN_FREE_RAM_GB:.1f} GB free."
        )

    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer
    from transformers.optimization import Adafactor

    torch.set_num_threads(max(1, min(2, os.cpu_count() or 1)))
    random.seed(42)
    torch.manual_seed(42)
    device = torch.device("cpu")
    tokenizer = AutoTokenizer.from_pretrained(args.base_model)
    if tokenizer.pad_token_id is None:
        tokenizer.pad_token = tokenizer.eos_token
    model = AutoModelForCausalLM.from_pretrained(args.base_model)
    model.config.use_cache = False
    model.to(device)
    rows = load_rows(args.dataset, tokenizer, args.max_length, args.max_samples)
    if len(rows) < 10:
        raise SystemExit(f"Only {len(rows)} usable samples were found; at least 10 are required.")

    optimizer = Adafactor(model.parameters(), lr=5e-5, relative_step=False,
                          scale_parameter=False, warmup_init=False)
    model.train()
    steps = 0
    started = time.time()
    for epoch in range(args.epochs):
        random.shuffle(rows)
        running_loss = 0.0
        interval_loss = 0.0
        interval_count = 0
        for row in rows:
            input_ids = row.unsqueeze(0).to(device)
            labels = input_ids.clone()
            optimizer.zero_grad(set_to_none=True)
            result = model(input_ids=input_ids, attention_mask=torch.ones_like(input_ids), labels=labels)
            loss = result.loss
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            optimizer.step()
            steps += 1
            loss_value = float(loss.detach())
            running_loss += loss_value
            interval_loss += loss_value
            interval_count += 1
            if interval_count == 25 or steps == len(rows) * args.epochs:
                elapsed = int(time.time() - started)
                epoch_steps = steps - epoch * len(rows)
                print(f"epoch={epoch + 1}/{args.epochs} step={steps}/{len(rows) * args.epochs} batch_loss={interval_loss / interval_count:.3f} mean_loss={running_loss / epoch_steps:.3f} elapsed_seconds={elapsed}", flush=True)
                interval_loss = 0.0
                interval_count = 0

    args.output.mkdir(parents=True, exist_ok=True)
    model.config.use_cache = True
    model.save_pretrained(args.output, safe_serialization=True)
    tokenizer.save_pretrained(args.output)
    print(f"Saved local prototype model to {args.output}", flush=True)


if __name__ == "__main__":
    main()
