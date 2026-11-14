"""Local OpenAI-compatible API for the fine-tuned Open-Kode prototype."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sqlite3
import threading
import time
import uuid
from datetime import date, datetime, timezone
from pathlib import Path
from wsgiref.simple_server import make_server


TRAINING_DIR = Path(__file__).resolve().parent
SITE_DIR = TRAINING_DIR.parent
DB_PATH = Path(os.environ.get("OPENKODE_API_DB", SITE_DIR / "runtime" / "model-api.sqlite3"))
MODEL_DIR = Path(os.environ.get("OPENKODE_MODEL_DIR", TRAINING_DIR / "output" / "openkode-distilgpt2"))
ADMIN_EMAIL = os.environ.get("OPENKODE_API_ADMIN_EMAIL", "mahir31891@gmail.com").strip().lower()
KEY_PATTERN = re.compile(r"^ok_live_[A-Za-z0-9_-]{32,}$")
MODEL_LOCK = threading.Lock()
MODEL = None
TOKENIZER = None
MAX_BODY_BYTES = 32 * 1024
REQUESTS_PER_MINUTE = 30


def connect() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(DB_PATH, timeout=10)
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA journal_mode=WAL")
    db.executescript("""
        CREATE TABLE IF NOT EXISTS model_api_keys (
            id TEXT PRIMARY KEY,
            email TEXT NOT NULL,
            label TEXT NOT NULL,
            key_hash TEXT NOT NULL UNIQUE,
            is_admin INTEGER NOT NULL DEFAULT 0,
            paid_until TEXT,
            created_at TEXT NOT NULL,
            last_used_at TEXT,
            revoked_at TEXT
        );
        CREATE TABLE IF NOT EXISTS model_api_usage (
            key_id TEXT PRIMARY KEY REFERENCES model_api_keys(id),
            window_start INTEGER NOT NULL,
            request_count INTEGER NOT NULL DEFAULT 0
        );
    """)
    return db


def create_api_key(email: str, label: str, paid_until: str | None = None) -> tuple[str, str]:
    normalized = email.strip().lower()
    if not normalized or "@" not in normalized:
        raise ValueError("Provide a valid account email.")
    if paid_until:
        date.fromisoformat(paid_until)
    is_admin = normalized == ADMIN_EMAIL
    if not is_admin and not paid_until:
        raise ValueError("Subscriber keys require --paid-until; payment checkout is not configured yet.")
    raw_key = "ok_live_" + os.urandom(32).hex()
    key_hash = hashlib.sha256(raw_key.encode("ascii")).hexdigest()
    key_id = uuid.uuid4().hex
    now = datetime.now(timezone.utc).isoformat()
    with connect() as db:
        db.execute(
            "INSERT INTO model_api_keys(id,email,label,key_hash,is_admin,paid_until,created_at) VALUES(?,?,?,?,?,?,?)",
            (key_id, normalized, label.strip()[:80] or "Open-Kode API key", key_hash, int(is_admin), paid_until, now),
        )
    return key_id, raw_key


def revoke_api_key(key_id: str) -> bool:
    now = datetime.now(timezone.utc).isoformat()
    with connect() as db:
        result = db.execute("UPDATE model_api_keys SET revoked_at=? WHERE id=? AND revoked_at IS NULL", (now, key_id))
        return result.rowcount == 1


def _json_response(start_response, status: str, payload: dict):
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    start_response(status, [
        ("Content-Type", "application/json; charset=utf-8"),
        ("Content-Length", str(len(body))),
        ("Cache-Control", "no-store"),
        ("X-Content-Type-Options", "nosniff"),
    ])
    return [body]


def _read_body(environ) -> dict:
    try:
        size = int(environ.get("CONTENT_LENGTH") or "0")
    except ValueError as exc:
        raise ValueError("Invalid request size.") from exc
    if size < 1 or size > MAX_BODY_BYTES:
        raise ValueError("Request body is empty or too large.")
    try:
        payload = json.loads(environ["wsgi.input"].read(size).decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError("Request must contain valid JSON.") from exc
    if not isinstance(payload, dict):
        raise ValueError("Request must contain a JSON object.")
    return payload


def _authenticate(environ):
    header = environ.get("HTTP_AUTHORIZATION", "")
    scheme, _, raw_key = header.partition(" ")
    if scheme.lower() != "bearer" or not KEY_PATTERN.fullmatch(raw_key):
        return None
    key_hash = hashlib.sha256(raw_key.encode("ascii")).hexdigest()
    today = date.today().isoformat()
    with connect() as db:
        row = db.execute(
            "SELECT * FROM model_api_keys WHERE key_hash=? AND revoked_at IS NULL",
            (key_hash,),
        ).fetchone()
        if row is None or (not row["is_admin"] and (not row["paid_until"] or row["paid_until"] < today)):
            return None
        now = int(time.time())
        usage = db.execute("SELECT * FROM model_api_usage WHERE key_id=?", (row["id"],)).fetchone()
        if usage and now - usage["window_start"] < 60 and usage["request_count"] >= REQUESTS_PER_MINUTE:
            return "rate_limited"
        if usage and now - usage["window_start"] < 60:
            db.execute("UPDATE model_api_usage SET request_count=request_count+1 WHERE key_id=?", (row["id"],))
        else:
            db.execute(
                "INSERT INTO model_api_usage(key_id,window_start,request_count) VALUES(?,?,1) "
                "ON CONFLICT(key_id) DO UPDATE SET window_start=excluded.window_start,request_count=1",
                (row["id"], now),
            )
        db.execute("UPDATE model_api_keys SET last_used_at=? WHERE id=?", (datetime.now(timezone.utc).isoformat(), row["id"]))
        return dict(row)


def _load_model():
    global MODEL, TOKENIZER
    if MODEL is not None:
        return MODEL, TOKENIZER
    with MODEL_LOCK:
        if MODEL is not None:
            return MODEL, TOKENIZER
        if not (MODEL_DIR / "config.json").is_file():
            raise FileNotFoundError("The local model has not been trained yet.")
        import torch
        from transformers import AutoModelForCausalLM, AutoTokenizer
        torch.set_num_threads(max(1, min(2, os.cpu_count() or 1)))
        TOKENIZER = AutoTokenizer.from_pretrained(MODEL_DIR)
        if TOKENIZER.pad_token_id is None:
            TOKENIZER.pad_token = TOKENIZER.eos_token
        MODEL = AutoModelForCausalLM.from_pretrained(MODEL_DIR)
        MODEL.eval()
        return MODEL, TOKENIZER


def _chat(environ, start_response):
    auth = _authenticate(environ)
    if auth == "rate_limited":
        return _json_response(start_response, "429 Too Many Requests", {"error": {"message": "Rate limit reached; retry in one minute.", "type": "rate_limit_error"}})
    if auth is None:
        return _json_response(start_response, "401 Unauthorized", {"error": {"message": "A valid, active Open-Kode API key is required.", "type": "authentication_error"}})
    try:
        payload = _read_body(environ)
        messages = payload.get("messages")
        if not isinstance(messages, list) or not messages:
            raise ValueError("Provide a non-empty messages array.")
        conversation = []
        for message in messages[-8:]:
            if not isinstance(message, dict) or message.get("role") not in {"system", "user", "assistant"}:
                continue
            content = message.get("content")
            if isinstance(content, str) and content.strip():
                label = "Open-Kode" if message["role"] == "assistant" else message["role"].capitalize()
                conversation.append(f"{label}: {content.strip()[:4000]}")
        prompt = "\n".join(conversation) + "\nOpen-Kode:"
        if len(prompt) > 12000:
            prompt = prompt[-12000:]
    except ValueError as exc:
        return _json_response(start_response, "400 Bad Request", {"error": {"message": str(exc), "type": "invalid_request_error"}})

    try:
        import torch
        model, tokenizer = _load_model()
        inputs = tokenizer(prompt, return_tensors="pt", truncation=True, max_length=384)
        with torch.inference_mode():
            output = model.generate(
                **inputs,
                max_new_tokens=100,
                do_sample=True,
                temperature=0.8,
                top_p=0.92,
                repetition_penalty=1.12,
                pad_token_id=tokenizer.eos_token_id,
            )
        answer = tokenizer.decode(output[0][inputs["input_ids"].shape[1]:], skip_special_tokens=True).strip()
        return _json_response(start_response, "200 OK", {
            "id": "chatcmpl-" + uuid.uuid4().hex[:16],
            "object": "chat.completion",
            "created": int(time.time()),
            "model": "openkode-local-prototype",
            "choices": [{"index": 0, "message": {"role": "assistant", "content": answer}, "finish_reason": "stop"}],
        })
    except FileNotFoundError as exc:
        return _json_response(start_response, "503 Service Unavailable", {"error": {"message": str(exc), "type": "model_unavailable"}})
    except Exception:
        return _json_response(start_response, "503 Service Unavailable", {"error": {"message": "The local Open-Kode model could not respond.", "type": "model_unavailable"}})


def application(environ, start_response):
    path = environ.get("PATH_INFO", "/")
    method = environ.get("REQUEST_METHOD", "GET").upper()
    if path == "/health" and method == "GET":
        return _json_response(start_response, "200 OK", {"service": "openkode-model-api", "model_ready": (MODEL_DIR / "config.json").is_file()})
    if path == "/v1/chat/completions" and method == "POST":
        return _chat(environ, start_response)
    return _json_response(start_response, "404 Not Found", {"error": {"message": "Route not found.", "type": "invalid_request_error"}})


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", default=os.environ.get("OPENKODE_MODEL_HOST", "127.0.0.1"))
    parser.add_argument("--port", type=int, default=int(os.environ.get("OPENKODE_MODEL_PORT", "9000")))
    args = parser.parse_args()
    connect().close()
    print(f"Open-Kode model API listening at http://{args.host}:{args.port}")
    print("Use /v1/chat/completions with an Open-Kode API key. This prototype binds to localhost by default.")
    with make_server(args.host, args.port, application) as server:
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            print("\nOpen-Kode model API stopped.")


if __name__ == "__main__":
    main()
