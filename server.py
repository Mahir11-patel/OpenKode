"""Open-Kode website server, account console, and KODE.MINI API."""
from __future__ import annotations

from datetime import date, datetime, timezone
import hashlib
import hmac
import importlib.util
import io
import json
import mimetypes
import os
import re
import secrets
import sqlite3
import sys
import threading
import time
import uuid
import zipfile
from contextlib import contextmanager
from http import cookies
from pathlib import Path
from urllib.parse import parse_qs, urlsplit
from wsgiref.simple_server import make_server

SITE_DIR = Path(__file__).resolve().parent
WORKSPACE_DIR = SITE_DIR.parent
CONTENT_FILE = SITE_DIR / "content.json"


def _load_local_env() -> None:
    """Load local development secrets without overriding server environment values."""
    env_path = SITE_DIR / ".env"
    if not env_path.is_file():
        return
    try:
        lines = env_path.read_text(encoding="utf-8").splitlines()
    except OSError:
        return
    for raw_line in lines:
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip()
        if value[:1] == value[-1:] and value.startswith(("'", '"')):
            value = value[1:-1]
        if key and key.replace("_", "").isalnum():
            os.environ.setdefault(key, value)


_load_local_env()
ADMIN_EMAIL = os.environ.get("OPENKODE_ADMIN_EMAIL", "mahir31891@gmail.com").strip().lower()
SESSION_TTL = 12 * 60 * 60
MAX_BODY_BYTES = 64 * 1024
ACCOUNT_DB_FILE = SITE_DIR / "runtime" / "openkode-accounts.sqlite3"
COOKIE_NAME = "openkode_admin"
COOKIE_SECURE = os.environ.get("OPENKODE_COOKIE_SECURE", "0") == "1"
API_KEY_PATTERN = re.compile(r"^ok_live_[A-Za-z0-9_-]{32,}$")
EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
API_REQUESTS_PER_MINUTE = 30

DEFAULT_CONTENT = {
    "hero_lead": "Build openly.",
    "hero_accent": "Go further.",
    "hero_description": "Open-Kode brings code, useful AI, and thoughtful software together so more people can turn ideas into things that work.",
    "about_heading_first": "Good ideas grow",
    "about_heading_second": "when they’re shared.",
    "about_description": "Open-Kode is a home for practical software and AI projects. Browse the source, learn how each piece works, and build something of your own.",
    "footer_description": "Useful software and AI,\nbuilt to be shared.",
}

CATALOG = [
    {
        "name": "KODE.MINI Python engine", "category_label": "AI · PYTHON",
        "description": "Explore the Python source for the KODE.MINI conversational assistant. The implementation describes itself as an offline, rule-based engine.",
        "categories": ["all", "ai", "code", "project"], "tags": ["Python", "99 KB", "MIT in source"],
        "icon": "PY", "detail_path": "/models/kode-mini", "download_id": "kode-mini-python", "download_label": "Get source ↓", "license_id": "kode-mini-readme", "license_label": "Project notes ↗",
    },
    {
        "name": "KODE.MINI project notes", "category_label": "PROJECT · README",
        "description": "Setup and usage notes for the expanded KODE.MINI package, including the included knowledge-base file.",
        "categories": ["all", "project"], "tags": ["Python", "Offline", "Project docs"],
        "icon": "↗", "detail_path": "/projects/kode-mini", "download_id": "kode-mini-readme", "download_label": "Read notes ↓", "license_id": "kode-mini-readme", "license_label": "Project notes ↗",
    },
    {
        "name": "Open-Kode website source", "category_label": "WEBSITE · FULL SOURCE",
        "description": "Download this site’s HTML, CSS, JavaScript, Python server, setup notes, and browser icon as a ZIP archive.",
        "categories": ["all", "code", "project"], "tags": ["HTML", "CSS", "JavaScript", "Python"],
        "icon": "{ }", "detail_path": "/projects/openkode-website", "download_id": "openkode-source", "download_label": "Get website source ↓", "license_id": "openkode-license", "license_label": "License ↗",
    },
    {
        "name": "Clawd for Windows", "category_label": "APP · WINDOWS",
        "description": "Download the Clawd desktop application build directly. This is an app installer build, not source code.",
        "categories": ["all", "project", "app"], "tags": ["Windows", "EXE", "8.6 MB"],
        "icon": "EXE", "detail_path": "/apps/clawd", "download_id": "app-clawd", "download_label": "Download app ↓", "license_id": "openkode-license", "license_label": "App details ↗",
    },
    {
        "name": "Ganesha for Windows", "category_label": "APP · WINDOWS",
        "description": "Download the Ganesha desktop application build directly. This is an app installer build, not source code.",
        "categories": ["all", "project", "app"], "tags": ["Windows", "EXE", "8.5 MB"],
        "icon": "EXE", "detail_path": "/apps/ganesha", "download_id": "app-ganesha", "download_label": "Download app ↓", "license_id": "openkode-license", "license_label": "App details ↗",
    },
    {
        "name": "Kode for Windows", "category_label": "APP · WINDOWS",
        "description": "Download the Kode desktop application build directly. This is an app installer build, not source code.",
        "categories": ["all", "project", "app"], "tags": ["Windows", "EXE", "8.4 MB"],
        "icon": "EXE", "detail_path": "/apps/kode", "download_id": "app-kode", "download_label": "Download app ↓", "license_id": "openkode-license", "license_label": "App details ↗",
    },
    {
        "name": "Minux for Windows", "category_label": "APP · WINDOWS",
        "description": "Download the Minux desktop application build directly. This is an app installer build, not source code.",
        "categories": ["all", "project", "app"], "tags": ["Windows", "EXE", "8.4 MB"],
        "icon": "EXE", "detail_path": "/apps/minux", "download_id": "app-minux", "download_label": "Download app ↓", "license_id": "openkode-license", "license_label": "App details ↗",
    },
]

DETAILS = {
    "kode-mini": {
        "title": "KODE.MINI", "category": "AI MODEL · PYTHON", "kind": "model",
        "summary": "A local-first conversational assistant implemented with Python decision rules.",
        "description": "KODE.MINI is an inspectable Python assistant that classifies prompts and produces responses from built-in rules and knowledge. It does not contain neural-network weights or call an external model API. Run the local server to try the model, or browse its source here.",
        "tags": ["Python", "Rule-based", "Offline", "No model weights"],
        "download_id": "kode-mini-python", "download_label": "Download Python source", "secondary_path": "/playground", "secondary_label": "Use the model",
        "notes": "The existing source file identifies its license as MIT. Keep its original author and license notice when redistributing it.",
    },
    "kode-mini-project": {
        "title": "KODE.MINI project", "category": "PROJECT · PYTHON", "kind": "project",
        "summary": "The complete KODE.MINI project notes and source entry point.",
        "description": "Read the package notes for the KODE.MINI offline assistant, then download the Python engine. The expanded knowledge-base data is not included in the public download listing until its redistribution terms are confirmed.",
        "tags": ["Python", "Project notes", "Offline assistant"],
        "download_id": "kode-mini-readme", "download_label": "Download project notes", "secondary_path": "/models/kode-mini", "secondary_label": "Model details",
        "notes": "The Python engine is available separately from the project notes.",
    },
    "openkode-website": {
        "title": "Open-Kode website", "category": "PROJECT · OPEN SOURCE", "kind": "project",
        "summary": "The full source for the Open-Kode website and Python server.",
        "description": "Download the website’s HTML, responsive CSS, JavaScript, PNG logo, and Python backend in one archive. The site includes a public library, account sign-in, the KODE.MINI AI playground, and API key management.",
        "tags": ["HTML", "CSS", "JavaScript", "Python", "MIT"],
        "download_id": "openkode-source", "download_label": "Download full website source", "secondary_path": "/", "secondary_label": "Back to home",
        "notes": "The Open-Kode website source is licensed under MIT. Account passwords are stored as salted scrypt hashes. The local Python server runs the account console and KODE.MINI API.",
    },
    "clawd": {"title": "Clawd", "category": "WINDOWS APP", "kind": "app", "summary": "A Windows application build from the Open-Kode workspace.", "description": "Download the Clawd Windows executable directly. The current workspace contains this built application, but does not include matching source code or separate product documentation.", "tags": ["Windows", "EXE", "8.6 MB"], "download_id": "app-clawd", "download_label": "Download Clawd for Windows", "secondary_path": "/#library", "secondary_label": "Browse other apps", "notes": "This download is an executable application, not source code. Verify the file before running it. No source or standalone license file was found for this build."},
    "ganesha": {"title": "Ganesha", "category": "WINDOWS APP", "kind": "app", "summary": "A Windows application build from the Open-Kode workspace.", "description": "Download the Ganesha Windows executable directly. The current workspace contains this built application, but does not include matching source code or separate product documentation.", "tags": ["Windows", "EXE", "8.5 MB"], "download_id": "app-ganesha", "download_label": "Download Ganesha for Windows", "secondary_path": "/#library", "secondary_label": "Browse other apps", "notes": "This download is an executable application, not source code. Verify the file before running it. No source or standalone license file was found for this build."},
    "kode": {"title": "Kode", "category": "WINDOWS APP", "kind": "app", "summary": "A Windows application build from the Open-Kode workspace.", "description": "Download the Kode Windows executable directly. The current workspace contains this built application, but does not include matching source code or separate product documentation.", "tags": ["Windows", "EXE", "8.4 MB"], "download_id": "app-kode", "download_label": "Download Kode for Windows", "secondary_path": "/#library", "secondary_label": "Browse other apps", "notes": "This download is an executable application, not source code. Verify the file before running it. No source or standalone license file was found for this build."},
    "minux": {"title": "Minux", "category": "WINDOWS APP", "kind": "app", "summary": "A Windows application build from the Open-Kode workspace.", "description": "Download the Minux Windows executable directly. The current workspace contains this built application, but does not include matching source code or separate product documentation.", "tags": ["Windows", "EXE", "8.4 MB"], "download_id": "app-minux", "download_label": "Download Minux for Windows", "secondary_path": "/#library", "secondary_label": "Browse other apps", "notes": "This download is an executable application, not source code. Verify the file before running it. No source or standalone license file was found for this build."},
}
DETAIL_ROUTES = {
    "/models/kode-mini": "kode-mini",
    "/projects/kode-mini": "kode-mini-project",
    "/projects/openkode-website": "openkode-website",
    "/apps/clawd": "clawd",
    "/apps/ganesha": "ganesha",
    "/apps/kode": "kode",
    "/apps/minux": "minux",
}
APP_FILES = {
    "app-clawd": (WORKSPACE_DIR / "Clawd.exe", "Clawd.exe"),
    "app-ganesha": (WORKSPACE_DIR / "Ganesha.exe", "Ganesha.exe"),
    "app-kode": (WORKSPACE_DIR / "Kode.exe", "Kode.exe"),
    "app-minux": (WORKSPACE_DIR / "Minux.exe", "Minux.exe"),
}

AUTH_LOCK = threading.Lock()
SESSIONS: dict[str, float] = {}
SESSION_USERS: dict[str, str] = {}
AUTH_ATTEMPTS: dict[str, list[float]] = {}
SIGNUP_ATTEMPTS: dict[str, list[float]] = {}
CHAT_HISTORY: dict[str, list[float]] = {}
AI_ENGINE = None
AI_ENGINE_LOCK = threading.Lock()
AI_CALL_LOCK = threading.Lock()


def _json_response(start_response, status: str, payload: dict, headers: list[tuple[str, str]] | None = None):
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    response_headers = [("Content-Type", "application/json; charset=utf-8"), ("Content-Length", str(len(body)),), ("Cache-Control", "no-store")]
    if headers:
        response_headers.extend(headers)
    start_response(status, response_headers)
    return [body]


def _cookie_header(value: str, max_age: int) -> tuple[str, str]:
    secure = "; Secure" if COOKIE_SECURE else ""
    return ("Set-Cookie", f"{COOKIE_NAME}={value}; HttpOnly; SameSite=Strict; Path=/; Max-Age={max_age}{secure}")


def _read_json(environ) -> dict:
    try:
        size = int(environ.get("CONTENT_LENGTH") or "0")
    except ValueError as exc:
        raise ValueError("Invalid request size.") from exc
    if size < 1 or size > MAX_BODY_BYTES:
        raise ValueError("Request body is empty or too large.")
    raw = environ["wsgi.input"].read(size)
    try:
        result = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError("Request must contain valid JSON.") from exc
    if not isinstance(result, dict):
        raise ValueError("Request must contain a JSON object.")
    return result


def _origin_allowed(environ) -> bool:
    origin = environ.get("HTTP_ORIGIN")
    if not origin:
        return True
    expected = os.environ.get("OPENKODE_ALLOWED_ORIGIN", "").strip().rstrip("/")
    if expected:
        return origin.rstrip("/") == expected
    origin_parts = urlsplit(origin)
    request_host = environ.get("HTTP_HOST", "").lower()
    return origin_parts.scheme in ("http", "https") and origin_parts.netloc.lower() == request_host


def _account_db() -> sqlite3.Connection:
    ACCOUNT_DB_FILE.parent.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(ACCOUNT_DB_FILE, timeout=10)
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA journal_mode=WAL")
    db.executescript("""
        CREATE TABLE IF NOT EXISTS accounts (
            email TEXT PRIMARY KEY COLLATE NOCASE,
            display_name TEXT NOT NULL,
            password_salt BLOB NOT NULL,
            password_hash BLOB NOT NULL,
            role TEXT NOT NULL CHECK(role IN ('admin', 'user')),
            created_at TEXT NOT NULL,
            last_login_at TEXT
        );
        CREATE TABLE IF NOT EXISTS kode_mini_api_keys (
            id TEXT PRIMARY KEY,
            email TEXT NOT NULL,
            label TEXT NOT NULL,
            key_prefix TEXT NOT NULL,
            key_hash TEXT NOT NULL UNIQUE,
            is_admin INTEGER NOT NULL DEFAULT 0,
            paid_until TEXT,
            created_at TEXT NOT NULL,
            last_used_at TEXT,
            revoked_at TEXT
        );
        CREATE TABLE IF NOT EXISTS kode_mini_api_usage (
            key_id TEXT PRIMARY KEY REFERENCES kode_mini_api_keys(id),
            window_start INTEGER NOT NULL,
            request_count INTEGER NOT NULL DEFAULT 0
        );
    """)
    return db


@contextmanager
def _account_connection():
    db = _account_db()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def _password_hash(password: str, salt: bytes) -> bytes:
    return hashlib.scrypt(password.encode("utf-8"), salt=salt, n=2**14, r=8, p=1, dklen=64,
                          maxmem=64 * 1024 * 1024)


def _new_password(password: str) -> tuple[bytes, bytes]:
    salt = secrets.token_bytes(16)
    return salt, _password_hash(password, salt)


def _verify_password(password: str, salt: bytes, expected: bytes) -> bool:
    try:
        actual = _password_hash(password, salt)
    except (ValueError, MemoryError):
        return False
    return hmac.compare_digest(actual, expected)


def _rate_limit(bucket: dict[str, list[float]], key: str, limit: int, window: int) -> bool:
    now = time.time()
    with AUTH_LOCK:
        attempts = [stamp for stamp in bucket.get(key, []) if stamp > now - window]
        if len(attempts) >= limit:
            bucket[key] = attempts
            return False
        attempts.append(now)
        bucket[key] = attempts
        return True


def _start_session(email: str) -> tuple[str, tuple[str, str]]:
    token = secrets.token_urlsafe(32)
    with AUTH_LOCK:
        SESSIONS[token] = time.time() + SESSION_TTL
        SESSION_USERS[token] = email
    return token, _cookie_header(token, SESSION_TTL)


def _session_token(environ) -> str | None:
    raw_cookie = environ.get("HTTP_COOKIE", "")
    parsed = cookies.SimpleCookie()
    try:
        parsed.load(raw_cookie)
    except cookies.CookieError:
        return None
    if COOKIE_NAME not in parsed:
        return None
    token = parsed[COOKIE_NAME].value
    with AUTH_LOCK:
        expiry = SESSIONS.get(token)
        if expiry is None:
            return None
        if expiry < time.time():
            SESSIONS.pop(token, None)
            SESSION_USERS.pop(token, None)
            return None
    return token


def _current_account(environ) -> dict | None:
    token = _session_token(environ)
    if token is None:
        return None
    with AUTH_LOCK:
        email = SESSION_USERS.get(token)
    if not email:
        return None
    with _account_connection() as db:
        row = db.execute(
            "SELECT email, display_name, role, created_at FROM accounts WHERE email=?",
            (email,),
        ).fetchone()
    return dict(row) if row else None


def _is_admin(environ) -> bool:
    account = _current_account(environ)
    return bool(account and account["role"] == "admin")


def _load_content() -> dict:
    if not CONTENT_FILE.exists():
        _write_content(DEFAULT_CONTENT)
    try:
        data = json.loads(CONTENT_FILE.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return DEFAULT_CONTENT.copy()
    if not isinstance(data, dict):
        return DEFAULT_CONTENT.copy()
    return {key: str(data.get(key, value)) for key, value in DEFAULT_CONTENT.items()}


def _write_content(content: dict) -> None:
    temporary = CONTENT_FILE.with_suffix(".tmp")
    temporary.write_text(json.dumps(content, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.replace(temporary, CONTENT_FILE)


def _validate_content(incoming: dict) -> dict:
    result = {}
    limits = {"hero_lead": 60, "hero_accent": 60, "hero_description": 500,
              "about_heading_first": 60, "about_heading_second": 60,
              "about_description": 500, "footer_description": 160}
    for key, limit in limits.items():
        value = incoming.get(key)
        if not isinstance(value, str):
            raise ValueError(f"{key.replace('_', ' ').capitalize()} is required.")
        value = value.strip()
        if not value or len(value) > limit:
            raise ValueError(f"{key.replace('_', ' ').capitalize()} must be 1 to {limit} characters.")
        result[key] = value
    return result


def _get_ai_engine():
    global AI_ENGINE
    if AI_ENGINE is not None:
        return AI_ENGINE
    with AI_ENGINE_LOCK:
        if AI_ENGINE is not None:
            return AI_ENGINE
        source_path = SITE_DIR / "kode_mini.py"
        if not source_path.is_file():
            source_path = WORKSPACE_DIR / "kode_mini_expanded_store" / "kode_mini.py"
        spec = importlib.util.spec_from_file_location("openkode_kode_mini", source_path)
        if spec is None or spec.loader is None:
            raise RuntimeError("Could not load the KODE.MINI Python source.")
        module = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = module
        spec.loader.exec_module(module)
        runtime = SITE_DIR / "runtime"
        AI_ENGINE = module.AirMiniEngine(
            model_path=str(runtime / "models"),
            data_path=str(runtime / "data"),
        )
        return AI_ENGINE


def _process_ai_message(message: str, user_id: str) -> dict:
    engine = _get_ai_engine()
    # KODE.MINI keeps short in-memory context. Filter it by account so one API key
    # cannot inherit another key's conversation context.
    with AI_CALL_LOCK:
        if hasattr(engine, "context_memory"):
            engine.context_memory = [
                entry for entry in engine.context_memory
                if entry.get("user_id") == user_id
            ][-5:]
        return engine.process(message, user_id=user_id)


def _create_kode_mini_key(email: str, label: str, paid_until: str | None) -> tuple[str, str]:
    normalized = email.strip().lower()
    if not EMAIL_PATTERN.fullmatch(normalized):
        raise ValueError("Enter a valid account email.")
    clean_label = label.strip()[:80] or "KODE.MINI API key"
    is_admin = normalized == ADMIN_EMAIL
    expiry = None
    if not is_admin:
        if not paid_until:
            raise ValueError("Set an active-through date for subscriber keys.")
        try:
            expiry = date.fromisoformat(paid_until).isoformat()
        except ValueError as exc:
            raise ValueError("Use a valid subscription date.") from exc
        if expiry < date.today().isoformat():
            raise ValueError("Subscriber access must end today or later.")
    raw_key = "ok_live_" + secrets.token_urlsafe(32)
    key_id = uuid.uuid4().hex
    now = datetime.now(timezone.utc).isoformat()
    with _account_connection() as db:
        db.execute(
            "INSERT INTO kode_mini_api_keys(id,email,label,key_prefix,key_hash,is_admin,paid_until,created_at) "
            "VALUES(?,?,?,?,?,?,?,?)",
            (key_id, normalized, clean_label, raw_key[:16],
             hashlib.sha256(raw_key.encode("ascii")).hexdigest(), int(is_admin), expiry, now),
        )
    return key_id, raw_key


def _list_kode_mini_keys() -> list[dict]:
    with _account_connection() as db:
        rows = db.execute(
            "SELECT id,email,label,key_prefix,is_admin,paid_until,created_at,last_used_at,revoked_at "
            "FROM kode_mini_api_keys ORDER BY created_at DESC LIMIT 200"
        ).fetchall()
    return [dict(row) for row in rows]


def _revoke_kode_mini_key(key_id: str) -> bool:
    if not re.fullmatch(r"[a-f0-9]{32}", key_id):
        return False
    now = datetime.now(timezone.utc).isoformat()
    with _account_connection() as db:
        updated = db.execute(
            "UPDATE kode_mini_api_keys SET revoked_at=? WHERE id=? AND revoked_at IS NULL",
            (now, key_id),
        )
    return updated.rowcount == 1


def _authenticate_kode_mini_key(environ) -> tuple[dict | None, bool]:
    header = environ.get("HTTP_AUTHORIZATION", "")
    scheme, _, raw_key = header.partition(" ")
    if scheme.lower() != "bearer" or not API_KEY_PATTERN.fullmatch(raw_key):
        return None, False
    key_hash = hashlib.sha256(raw_key.encode("ascii")).hexdigest()
    today = date.today().isoformat()
    now = int(time.time())
    with _account_connection() as db:
        row = db.execute(
            "SELECT * FROM kode_mini_api_keys WHERE key_hash=? AND revoked_at IS NULL",
            (key_hash,),
        ).fetchone()
        if row is None or (not row["is_admin"] and (not row["paid_until"] or row["paid_until"] < today)):
            return None, False
        usage = db.execute(
            "SELECT window_start,request_count FROM kode_mini_api_usage WHERE key_id=?",
            (row["id"],),
        ).fetchone()
        if usage and now - usage["window_start"] < 60:
            if usage["request_count"] >= API_REQUESTS_PER_MINUTE:
                return None, True
            db.execute(
                "UPDATE kode_mini_api_usage SET request_count=request_count+1 WHERE key_id=?",
                (row["id"],),
            )
        else:
            db.execute(
                "INSERT INTO kode_mini_api_usage(key_id,window_start,request_count) VALUES(?,?,1) "
                "ON CONFLICT(key_id) DO UPDATE SET window_start=excluded.window_start,request_count=1",
                (row["id"], now),
            )
        db.execute(
            "UPDATE kode_mini_api_keys SET last_used_at=? WHERE id=?",
            (datetime.now(timezone.utc).isoformat(), row["id"]),
        )
        return dict(row), False


def _file_bytes(file_path: Path) -> bytes:
    try:
        resolved = file_path.resolve(strict=True)
        resolved.relative_to(WORKSPACE_DIR.resolve())
    except (OSError, ValueError) as exc:
        raise FileNotFoundError from exc
    if not resolved.is_file():
        raise FileNotFoundError
    return resolved.read_bytes()


def _kode_mini_source_path() -> Path:
    local_copy = SITE_DIR / "kode_mini.py"
    return local_copy if local_copy.is_file() else WORKSPACE_DIR / "kode_mini_expanded_store" / "kode_mini.py"


def _download(download_id: str) -> tuple[bytes, str, str]:
    files = {
        "kode-mini-python": (_kode_mini_source_path(), "kode_mini.py", "text/x-python; charset=utf-8"),
        "kode-mini-readme": (WORKSPACE_DIR / "kode_mini_expanded_store" / "README.md", "KODE-MINI-README.md", "text/markdown; charset=utf-8"),
        "openkode-license": (SITE_DIR / "LICENSE", "LICENSE", "text/plain; charset=utf-8"),
    }
    if download_id in files:
        path, filename, content_type = files[download_id]
        return _file_bytes(path), filename, content_type
    if download_id in APP_FILES:
        path, filename = APP_FILES[download_id]
        return _file_bytes(path), filename, "application/octet-stream"
    if download_id == "openkode-source":
        output = io.BytesIO()
        archive_files = [
            (SITE_DIR / "index.html", "openkode-site/index.html"),
            (SITE_DIR / "console.html", "openkode-site/console.html"),
            (SITE_DIR / "console.css", "openkode-site/console.css"),
            (SITE_DIR / "console.js", "openkode-site/console.js"),
            (SITE_DIR / "styles.css", "openkode-site/styles.css"),
            (SITE_DIR / "app.js", "openkode-site/app.js"),
            (SITE_DIR / "server.py", "openkode-site/server.py"),
            (_kode_mini_source_path(), "openkode-site/kode_mini.py"),
            (SITE_DIR / "README.md", "openkode-site/README.md"),
            (SITE_DIR / "LICENSE", "openkode-site/LICENSE"),
            (SITE_DIR / ".env.example", "openkode-site/.env.example"),
            (SITE_DIR / ".gitignore", "openkode-site/.gitignore"),
            (SITE_DIR / "content.json", "openkode-site/content.json"),
            (SITE_DIR / "detail.html", "openkode-site/detail.html"),
            (SITE_DIR / "detail.js", "openkode-site/detail.js"),
            (SITE_DIR / "playground.html", "openkode-site/playground.html"),
            (SITE_DIR / "playground.js", "openkode-site/playground.js"),
            (SITE_DIR / "training" / "README.md", "openkode-site/training/README.md"),
            (SITE_DIR / "training" / "requirements.txt", "openkode-site/training/requirements.txt"),
            (SITE_DIR / "training" / "prepare_dataset.py", "openkode-site/training/prepare_dataset.py"),
            (SITE_DIR / "training" / "train_local.py", "openkode-site/training/train_local.py"),
            (SITE_DIR / "training" / "api_server.py", "openkode-site/training/api_server.py"),
            (SITE_DIR / "training" / "manage_api_key.py", "openkode-site/training/manage_api_key.py"),
            (SITE_DIR / "assets" / "favicon.png", "openkode-site/assets/favicon.png"),
            (SITE_DIR / "netlify.toml", "openkode-site/netlify.toml"),
            (SITE_DIR / "package.json", "openkode-site/package.json"),
            (SITE_DIR / "package-lock.json", "openkode-site/package-lock.json"),
            (SITE_DIR / "_headers", "openkode-site/_headers"),
            (SITE_DIR / "scripts" / "prepare-netlify.mjs", "openkode-site/scripts/prepare-netlify.mjs"),
            (SITE_DIR / "netlify" / "functions" / "api.mjs", "openkode-site/netlify/functions/api.mjs"),
            (SITE_DIR / "netlify" / "functions" / "auth.mjs", "openkode-site/netlify/functions/auth.mjs"),
            (SITE_DIR / "netlify" / "functions" / "shared.mjs", "openkode-site/netlify/functions/shared.mjs"),
            (SITE_DIR / "netlify" / "functions" / "site-data.json", "openkode-site/netlify/functions/site-data.json"),
        ]
        with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED) as archive:
            for path, name in archive_files:
                archive.writestr(name, _file_bytes(path))
        return output.getvalue(), "openkode-source.zip", "application/zip"
    raise FileNotFoundError


def application(environ, start_response):
    path = urlsplit(environ.get("PATH_INFO", "/")).path
    method = environ.get("REQUEST_METHOD", "GET").upper()
    if method == "OPTIONS":
        return _json_response(start_response, "405 Method Not Allowed", {"error": "Method not allowed."})

    common_headers = [("X-Content-Type-Options", "nosniff"), ("Referrer-Policy", "strict-origin-when-cross-origin"), ("X-Frame-Options", "DENY"), ("Permissions-Policy", "camera=(), microphone=(), geolocation=()"), ("Content-Security-Policy", "default-src 'self'; img-src 'self' data:; style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; font-src 'self' https://fonts.gstatic.com; script-src 'self'; connect-src 'self'; base-uri 'self'; form-action 'self'; frame-ancestors 'none'; object-src 'none'")]

    if path.startswith("/api/") and method == "GET" and path == "/api/content":
        return _json_response(start_response, "200 OK", _load_content(), common_headers)
    if path == "/api/catalog" and method == "GET":
        return _json_response(start_response, "200 OK", {"items": CATALOG}, common_headers)
    if path == "/api/items" and method == "GET":
        requested_path = parse_qs(environ.get("QUERY_STRING", "")).get("path", [""])[0]
        slug = DETAIL_ROUTES.get(requested_path)
        detail = DETAILS.get(slug)
        if detail is None:
            return _json_response(start_response, "404 Not Found", {"error": "Item not found."}, common_headers)
        return _json_response(start_response, "200 OK", detail, common_headers)
    if path == "/api/admin/session" and method == "GET":
        account = _current_account(environ)
        return _json_response(start_response, "200 OK", {"authenticated": bool(account and account["role"] == "admin")}, common_headers)
    if path == "/api/auth/session" and method == "GET":
        account = _current_account(environ)
        if not account:
            return _json_response(start_response, "200 OK", {"authenticated": False}, common_headers)
        account["is_admin"] = account["role"] == "admin"
        return _json_response(start_response, "200 OK", {"authenticated": True, "account": account}, common_headers)
    if path == "/api/admin/model-keys" and method == "GET":
        if not _is_admin(environ):
            return _json_response(start_response, "401 Unauthorized", {"error": "Sign in as the company administrator to manage KODE.MINI API keys."}, common_headers)
        return _json_response(start_response, "200 OK", {"keys": _list_kode_mini_keys()}, common_headers)
    if path == "/api/admin/accounts" and method == "GET":
        if not _is_admin(environ):
            return _json_response(start_response, "401 Unauthorized", {"error": "Sign in as the company administrator to view accounts."}, common_headers)
        with _account_connection() as db:
            rows = db.execute(
                "SELECT email,display_name,role,created_at,last_login_at FROM accounts ORDER BY created_at DESC LIMIT 500"
            ).fetchall()
        return _json_response(start_response, "200 OK", {"accounts": [dict(row) for row in rows]}, common_headers)

    if path in ("/api/auth/register", "/api/auth/login", "/api/account/password", "/api/admin/content", "/api/admin/model-keys", "/api/admin/model-keys/revoke", "/api/auth/logout") and method == "POST":
        if not _origin_allowed(environ):
            return _json_response(start_response, "403 Forbidden", {"error": "Request origin was not allowed."}, common_headers)
        try:
            body = _read_json(environ)
        except ValueError as exc:
            return _json_response(start_response, "400 Bad Request", {"error": str(exc)}, common_headers)

        if path == "/api/auth/register":
            email = str(body.get("email", "")).strip().lower()
            display_name = str(body.get("display_name", "")).strip()
            password = body.get("password")
            if not EMAIL_PATTERN.fullmatch(email):
                return _json_response(start_response, "400 Bad Request", {"error": "Enter a valid email address."}, common_headers)
            if not display_name or len(display_name) > 80:
                return _json_response(start_response, "400 Bad Request", {"error": "Name must be between 1 and 80 characters."}, common_headers)
            if not isinstance(password, str) or len(password) < 10 or len(password) > 256:
                return _json_response(start_response, "400 Bad Request", {"error": "Use a password between 10 and 256 characters."}, common_headers)
            remote_ip = environ.get("REMOTE_ADDR", "unknown")
            if not _rate_limit(SIGNUP_ATTEMPTS, remote_ip, 5, 3600):
                return _json_response(start_response, "429 Too Many Requests", {"error": "Too many new accounts from this device. Try again later."}, common_headers)
            if email == ADMIN_EMAIL:
                import ipaddress
                try:
                    if not ipaddress.ip_address(remote_ip).is_loopback:
                        return _json_response(start_response, "403 Forbidden", {"error": "Set up the company owner account on the computer running the local server."}, common_headers)
                except ValueError:
                    return _json_response(start_response, "403 Forbidden", {"error": "Set up the company owner account on the computer running the local server."}, common_headers)
            salt, hashed = _new_password(password)
            role = "admin" if email == ADMIN_EMAIL else "user"
            now = datetime.now(timezone.utc).isoformat()
            try:
                with _account_connection() as db:
                    db.execute(
                        "INSERT INTO accounts(email,display_name,password_salt,password_hash,role,created_at) VALUES(?,?,?,?,?,?)",
                        (email, display_name, salt, hashed, role, now),
                    )
            except sqlite3.IntegrityError:
                return _json_response(start_response, "409 Conflict", {"error": "An account already uses that email. Sign in instead."}, common_headers)
            token, cookie = _start_session(email)
            account = {"email": email, "display_name": display_name, "role": role, "created_at": now, "is_admin": role == "admin"}
            return _json_response(start_response, "201 Created", {"authenticated": True, "account": account}, common_headers + [cookie])

        if path == "/api/auth/login":
            email = str(body.get("email", "")).strip().lower()
            password = body.get("password")
            remote_ip = environ.get("REMOTE_ADDR", "unknown")
            attempt_key = f"{email}|{remote_ip}"
            if not _rate_limit(AUTH_ATTEMPTS, attempt_key, 5, 300):
                return _json_response(start_response, "429 Too Many Requests", {"error": "Too many sign-in attempts. Wait five minutes and try again."}, common_headers)
            with _account_connection() as db:
                row = db.execute("SELECT * FROM accounts WHERE email=?", (email,)).fetchone()
                valid = bool(row and isinstance(password, str) and _verify_password(password, row["password_salt"], row["password_hash"]))
                if valid:
                    now = datetime.now(timezone.utc).isoformat()
                    db.execute("UPDATE accounts SET last_login_at=? WHERE email=?", (now, email))
            if not valid:
                return _json_response(start_response, "401 Unauthorized", {"error": "Email or password is incorrect."}, common_headers)
            account = {"email": row["email"], "display_name": row["display_name"], "role": row["role"], "created_at": row["created_at"], "is_admin": row["role"] == "admin"}
            token, cookie = _start_session(row["email"])
            with AUTH_LOCK:
                AUTH_ATTEMPTS.pop(attempt_key, None)
            return _json_response(start_response, "200 OK", {"authenticated": True, "account": account}, common_headers + [cookie])

        if path == "/api/admin/content":
            if not _is_admin(environ):
                return _json_response(start_response, "403 Forbidden", {"error": "Only the company owner can edit the homepage."}, common_headers)
            try:
                content = _validate_content(body)
                _write_content(content)
            except (ValueError, OSError) as exc:
                return _json_response(start_response, "400 Bad Request", {"error": str(exc)}, common_headers)
            return _json_response(start_response, "200 OK", {"saved": True, "content": content}, common_headers)

        if path == "/api/admin/model-keys":
            if not _is_admin(environ):
                return _json_response(start_response, "403 Forbidden", {"error": "Only the company owner can issue KODE.MINI API keys."}, common_headers)
            try:
                key_id, raw_key = _create_kode_mini_key(
                    str(body.get("email", "")), str(body.get("label", "")),
                    str(body.get("paid_until", "")).strip() or None,
                )
            except (ValueError, OSError) as exc:
                return _json_response(start_response, "400 Bad Request", {"error": str(exc)}, common_headers)
            return _json_response(start_response, "201 Created", {"id": key_id, "api_key": raw_key}, common_headers)

        if path == "/api/admin/model-keys/revoke":
            if not _is_admin(environ):
                return _json_response(start_response, "403 Forbidden", {"error": "Only the company owner can revoke KODE.MINI API keys."}, common_headers)
            if not _revoke_kode_mini_key(str(body.get("id", ""))):
                return _json_response(start_response, "404 Not Found", {"error": "No active KODE.MINI API key matched that id."}, common_headers)
            return _json_response(start_response, "200 OK", {"revoked": True}, common_headers)

        if path == "/api/account/password":
            account = _current_account(environ)
            if not account:
                return _json_response(start_response, "401 Unauthorized", {"error": "Sign in again to change your password."}, common_headers)
            old_password, new_password = body.get("current_password"), body.get("new_password")
            if not isinstance(new_password, str) or len(new_password) < 10 or len(new_password) > 256:
                return _json_response(start_response, "400 Bad Request", {"error": "Use a new password between 10 and 256 characters."}, common_headers)
            with _account_connection() as db:
                row = db.execute("SELECT password_salt,password_hash FROM accounts WHERE email=?", (account["email"],)).fetchone()
                if not row or not isinstance(old_password, str) or not _verify_password(old_password, row["password_salt"], row["password_hash"]):
                    return _json_response(start_response, "401 Unauthorized", {"error": "Current password is incorrect."}, common_headers)
                salt, hashed = _new_password(new_password)
                db.execute("UPDATE accounts SET password_salt=?,password_hash=? WHERE email=?", (salt, hashed, account["email"]))
            return _json_response(start_response, "200 OK", {"changed": True}, common_headers)

        if path == "/api/auth/logout":
            token = _session_token(environ)
            if token:
                with AUTH_LOCK:
                    SESSIONS.pop(token, None)
                    SESSION_USERS.pop(token, None)
            clear_cookie = _cookie_header("", 0)
            return _json_response(start_response, "200 OK", {"signed_out": True}, common_headers + [clear_cookie])

    if path == "/v1/models" and method == "GET":
        api_key, limited = _authenticate_kode_mini_key(environ)
        if limited:
            return _json_response(start_response, "429 Too Many Requests", {"error": {"message": "Rate limit reached; retry in one minute.", "type": "rate_limit_error"}}, common_headers)
        if not api_key:
            return _json_response(start_response, "401 Unauthorized", {"error": {"message": "A valid, active Open-Kode API key is required.", "type": "authentication_error"}}, common_headers)
        return _json_response(start_response, "200 OK", {"object": "list", "data": [{"id": "kode-mini", "object": "model", "owned_by": "open-kode"}]}, common_headers)

    if path == "/v1/chat/completions" and method == "POST":
        if not _origin_allowed(environ):
            return _json_response(start_response, "403 Forbidden", {"error": {"message": "Browser cross-origin requests are not enabled. Call this API from your server.", "type": "invalid_request_error"}}, common_headers)
        api_key, limited = _authenticate_kode_mini_key(environ)
        if limited:
            return _json_response(start_response, "429 Too Many Requests", {"error": {"message": "Rate limit reached; retry in one minute.", "type": "rate_limit_error"}}, common_headers)
        if not api_key:
            return _json_response(start_response, "401 Unauthorized", {"error": {"message": "A valid, active Open-Kode API key is required.", "type": "authentication_error"}}, common_headers)
        try:
            body = _read_json(environ)
            model = body.get("model", "kode-mini")
            messages = body.get("messages")
            if model not in ("kode-mini", "KODE.MINI"):
                raise ValueError("The available model id is kode-mini.")
            if not isinstance(messages, list) or not messages or len(messages) > 40:
                raise ValueError("Provide 1 to 40 chat messages.")
            user_message = next((entry for entry in reversed(messages)
                                 if isinstance(entry, dict) and entry.get("role") == "user"), None)
            content = user_message.get("content") if user_message else None
            if not isinstance(content, str) or not content.strip() or len(content) > 2000:
                raise ValueError("The latest user message must contain 1 to 2,000 characters of text.")
        except ValueError as exc:
            return _json_response(start_response, "400 Bad Request", {"error": {"message": str(exc), "type": "invalid_request_error"}}, common_headers)
        try:
            result = _process_ai_message(content.strip(), f"api:{api_key['id']}")
        except Exception:
            return _json_response(start_response, "503 Service Unavailable", {"error": {"message": "KODE.MINI could not start. Check the Python model files and try again.", "type": "server_error"}}, common_headers)
        return _json_response(start_response, "200 OK", {
            "id": "chatcmpl-" + uuid.uuid4().hex[:20],
            "object": "chat.completion",
            "created": int(time.time()),
            "model": "kode-mini",
            "choices": [{"index": 0, "message": {"role": "assistant", "content": str(result.get("response", ""))}, "finish_reason": "stop"}],
            "kode_mini": {"intent": str(result.get("intent", "unknown")), "confidence": result.get("confidence", 0)},
        }, common_headers)

    if path == "/api/chat" and method == "POST":
        if not _origin_allowed(environ):
            return _json_response(start_response, "403 Forbidden", {"error": "Request origin was not allowed."}, common_headers)
        try:
            body = _read_json(environ)
        except ValueError as exc:
            return _json_response(start_response, "400 Bad Request", {"error": str(exc)}, common_headers)
        message = body.get("message")
        user_id = body.get("user_id", "web-demo")
        if not isinstance(message, str) or not message.strip() or len(message) > 1000:
            return _json_response(start_response, "400 Bad Request", {"error": "Enter a message up to 1,000 characters."}, common_headers)
        if not isinstance(user_id, str) or len(user_id) > 80:
            return _json_response(start_response, "400 Bad Request", {"error": "Invalid demo session."}, common_headers)
        now = time.time()
        remote_ip = environ.get("REMOTE_ADDR", "unknown")
        with AUTH_LOCK:
            recent = [stamp for stamp in CHAT_HISTORY.get(remote_ip, []) if stamp > now - 60]
            if len(recent) >= 30:
                CHAT_HISTORY[remote_ip] = recent
                return _json_response(start_response, "429 Too Many Requests", {"error": "Too many messages. Wait a minute and try again."}, common_headers)
            recent.append(now)
            CHAT_HISTORY[remote_ip] = recent
        try:
            result = _process_ai_message(message.strip(), f"demo:{user_id}")
        except Exception:
            return _json_response(start_response, "503 Service Unavailable", {"error": "KODE.MINI could not start. Check the Python model files and try again."}, common_headers)
        return _json_response(start_response, "200 OK", {"response": str(result.get("response", "")), "intent": str(result.get("intent", "unknown")), "confidence": result.get("confidence", 0)}, common_headers)

    if path == "/api/download" and method == "GET":
        download_id = parse_qs(environ.get("QUERY_STRING", "")).get("id", [""])[0]
        try:
            content, filename, content_type = _download(download_id)
        except FileNotFoundError:
            return _json_response(start_response, "404 Not Found", {"error": "This public download is not available."}, common_headers)
        headers = common_headers + [("Content-Type", content_type), ("Content-Length", str(len(content))), ("Content-Disposition", f'attachment; filename="{filename}"'), ("Cache-Control", "public, max-age=300")]
        start_response("200 OK", headers)
        return [content]

    if method != "GET" and method != "HEAD":
        return _json_response(start_response, "405 Method Not Allowed", {"error": "Method not allowed."}, common_headers)
    if path == "/playground" or path == "/playground/":
        path = "/playground.html"
    if path == "/console" or path == "/console/":
        path = "/console.html"
    if path in DETAIL_ROUTES:
        path = "/detail.html"
    relative = "index.html" if path == "/" else path.lstrip("/")
    try:
        target = (SITE_DIR / relative).resolve(strict=True)
        target.relative_to(SITE_DIR.resolve())
        relative_parts = target.relative_to(SITE_DIR.resolve()).parts
        if any(part.startswith(".") or part in {"runtime", "__pycache__"} for part in relative_parts):
            raise FileNotFoundError
        if not target.is_file():
            raise FileNotFoundError
        body = target.read_bytes()
    except (OSError, ValueError):
        return _json_response(start_response, "404 Not Found", {"error": "Page not found."}, common_headers)
    content_type = mimetypes.guess_type(str(target))[0] or "application/octet-stream"
    if content_type.startswith("text/") or content_type in ("application/javascript", "application/json", "image/svg+xml"):
        content_type += "; charset=utf-8"
    headers = common_headers + [("Content-Type", content_type), ("Content-Length", str(len(body))), ("Cache-Control", "no-cache")]
    start_response("200 OK", headers)
    return [b"" if method == "HEAD" else body]


def main() -> None:
    host = os.environ.get("OPENKODE_HOST", "127.0.0.1")
    try:
        port = int(os.environ.get("OPENKODE_PORT", "8000"))
    except ValueError as exc:
        raise SystemExit("OPENKODE_PORT must be a number.") from exc
    with _account_connection() as db:
        db.execute("SELECT 1")
    print(f"Open-Kode is serving at http://{host}:{port}")
    print("Accounts use email and password. Passwords are stored as salted scrypt hashes.")
    print("KODE.MINI API: http://127.0.0.1:8000/v1/chat/completions (bearer key required).")
    with make_server(host, port, application) as server:
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            print("\nOpen-Kode server stopped.")


if __name__ == "__main__":
    main()




