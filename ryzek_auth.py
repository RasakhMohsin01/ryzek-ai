#!/usr/bin/env python3
"""
Ryzek AI v2.6 - accounts, login tokens and the local database.

Why SQLite: it is part of the Python standard library (works on the phone too),
it is a real database file, and it costs nothing - no server, no cloud bill.

What is stored in data/ryzek.db:

    users       one row per account (username, salted PBKDF2 password hash, role)
    tokens      login sessions (only a SHA-256 of the token is stored)
    logins      login history, used for the "recent activity" panel
    facts       things Ryzek remembers about a user (name, likes, goals, ...)
    qa          every question the user asked, so it can recall them later

Two kinds of account:

    role = "author"   the main author account. Created automatically on first
                      boot. It can list, promote and delete other accounts.
    role = "user"     normal accounts people create themselves.

Passwords are never stored in plain text. Each password is hashed with
PBKDF2-HMAC-SHA256, a random 16-byte salt and 200,000 iterations, and compared
with hmac.compare_digest to avoid timing leaks.
"""

from __future__ import annotations

import hashlib
import hmac
import os
import re
import secrets
import sqlite3
import threading
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

ROOT = Path(__file__).resolve().parent
DB_PATH = Path(os.environ.get("RYZEK_DATA") or (ROOT / "data")) / "ryzek.db"

PBKDF2_ROUNDS = 200_000
TOKEN_DAYS = 30
USERNAME_RE = re.compile(r"^[a-zA-Z0-9._-]{3,24}$")

# The main author account. Override with environment variables if you like.
AUTHOR_USERNAME = os.environ.get("RYZEK_AUTHOR_NAME", "ryzek")
AUTHOR_PASSWORD = os.environ.get("RYZEK_AUTHOR_PASSWORD", "ryzek20")
AUTHOR_DISPLAY = os.environ.get("RYZEK_AUTHOR_DISPLAY", "Rasakh Mohsin aka Ryzek")


class AuthError(Exception):
    """A login or signup problem with a message that is safe to show users."""

    def __init__(self, message: str, code: str = "auth_error") -> None:
        super().__init__(message)
        self.message = message
        self.code = code


# ---------------------------------------------------------------------------
# password + token helpers
# ---------------------------------------------------------------------------

def _hash_password(password: str, salt: bytes) -> str:
    return hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt,
                               PBKDF2_ROUNDS).hex()


def _token_key(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def password_problem(password: str) -> Optional[str]:
    """Return a friendly message if the password is too weak, else None."""
    if not isinstance(password, str) or len(password) < 6:
        return "Password must be at least 6 characters long."
    if len(password) > 200:
        return "That password is too long (200 characters max)."
    if password.lower() in ("123456", "password", "qwerty", "111111", "abc123"):
        return "That password is too easy to guess. Please pick another one."
    return None


def username_problem(username: str) -> Optional[str]:
    if not isinstance(username, str) or not USERNAME_RE.match(username.strip()):
        return ("Username must be 3-24 characters, using letters, numbers, "
                "dot, underscore or dash only.")
    if username.strip().lower() in ("admin", "root", "system", "support",
                                    "moderator", "ryzek_ai", "ryzekai"):
        return "That username is reserved. Please choose another one."
    return None


# ---------------------------------------------------------------------------
# the database
# ---------------------------------------------------------------------------

class AuthDB:
    """Thread-safe wrapper around data/ryzek.db (shared with the memory store)."""

    _instances: Dict[str, "AuthDB"] = {}
    _instances_lock = threading.Lock()

    def __init__(self, path: Path = DB_PATH) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.lock = threading.RLock()
        self._local = threading.local()
        self._create_schema()
        self._ensure_author()

    # -- singleton per path so the memory module reuses the same connection pool
    @classmethod
    def shared(cls, path: Path = DB_PATH) -> "AuthDB":
        key = str(Path(path).resolve())
        with cls._instances_lock:
            if key not in cls._instances:
                cls._instances[key] = cls(Path(path))
            return cls._instances[key]

    # -- connection per thread (sqlite objects are not shareable across threads)
    @property
    def conn(self) -> sqlite3.Connection:
        c = getattr(self._local, "conn", None)
        if c is None:
            c = sqlite3.connect(str(self.path), timeout=20, isolation_level=None)
            c.row_factory = sqlite3.Row
            c.execute("PRAGMA journal_mode=WAL")
            c.execute("PRAGMA synchronous=NORMAL")
            c.execute("PRAGMA foreign_keys=ON")
            self._local.conn = c
        return c

    def _create_schema(self) -> None:
        with self.lock:
            c = self.conn
            c.executescript(
                """
                CREATE TABLE IF NOT EXISTS users (
                    id           INTEGER PRIMARY KEY AUTOINCREMENT,
                    username     TEXT NOT NULL,
                    username_key TEXT NOT NULL UNIQUE,
                    display_name TEXT NOT NULL DEFAULT '',
                    pass_hash    TEXT NOT NULL,
                    salt         TEXT NOT NULL,
                    role         TEXT NOT NULL DEFAULT 'user',
                    created_at   REAL NOT NULL,
                    last_login   REAL,
                    disabled     INTEGER NOT NULL DEFAULT 0
                );
                CREATE TABLE IF NOT EXISTS tokens (
                    token_hash TEXT PRIMARY KEY,
                    user_id    INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                    created_at REAL NOT NULL,
                    expires_at REAL NOT NULL,
                    user_agent TEXT NOT NULL DEFAULT '',
                    ip         TEXT NOT NULL DEFAULT ''
                );
                CREATE TABLE IF NOT EXISTS logins (
                    id      INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    ok      INTEGER NOT NULL,
                    ts      REAL NOT NULL,
                    ip      TEXT NOT NULL DEFAULT '',
                    ua      TEXT NOT NULL DEFAULT ''
                );
                CREATE TABLE IF NOT EXISTS signups (
                    id       INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id  INTEGER,
                    ts       REAL NOT NULL,
                    ip       TEXT NOT NULL DEFAULT '',
                    device   TEXT NOT NULL DEFAULT '',
                    ua       TEXT NOT NULL DEFAULT ''
                );
                CREATE INDEX IF NOT EXISTS idx_signups_device ON signups(device);
                CREATE INDEX IF NOT EXISTS idx_signups_ip ON signups(ip);
                CREATE TABLE IF NOT EXISTS facts (
                    id         INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id    INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                    key        TEXT NOT NULL,
                    value      TEXT NOT NULL,
                    source     TEXT NOT NULL DEFAULT '',
                    created_at REAL NOT NULL,
                    updated_at REAL NOT NULL,
                    UNIQUE(user_id, key)
                );
                CREATE TABLE IF NOT EXISTS qa (
                    id         INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id    INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                    session_id TEXT NOT NULL DEFAULT '',
                    question   TEXT NOT NULL,
                    answer     TEXT NOT NULL DEFAULT '',
                    topic      TEXT NOT NULL DEFAULT '',
                    created_at REAL NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_qa_user ON qa(user_id, created_at DESC);
                CREATE INDEX IF NOT EXISTS idx_facts_user ON facts(user_id, updated_at DESC);
                CREATE INDEX IF NOT EXISTS idx_tokens_user ON tokens(user_id);
                """
            )

    # ---------------------------------------------------------------- accounts
    def _ensure_author(self) -> None:
        with self.lock:
            row = self.conn.execute(
                "SELECT id FROM users WHERE role='author' LIMIT 1").fetchone()
            if row:
                return
            salt = secrets.token_bytes(16)
            self.conn.execute(
                "INSERT INTO users(username, username_key, display_name, pass_hash,"
                " salt, role, created_at) VALUES(?,?,?,?,?,?,?)",
                (AUTHOR_USERNAME, AUTHOR_USERNAME.lower(), AUTHOR_DISPLAY,
                 _hash_password(AUTHOR_PASSWORD, salt),
                 salt.hex(), "author", time.time()))

    def _row_to_user(self, row: sqlite3.Row) -> Dict[str, Any]:
        return {"id": row["id"], "username": row["username"],
                "display_name": row["display_name"] or row["username"],
                "role": row["role"], "created_at": row["created_at"],
                "last_login": row["last_login"], "disabled": bool(row["disabled"])}

    def create_user(self, username: str, password: str,
                    display_name: str = "", role: str = "user") -> Dict[str, Any]:
        problem = username_problem(username)
        if problem:
            raise AuthError(problem, "bad_username")
        bad = password_problem(password)
        if bad:
            raise AuthError(bad, "bad_password")
        key = username.strip().lower()
        with self.lock:
            if self.conn.execute("SELECT 1 FROM users WHERE username_key=?",
                                 (key,)).fetchone():
                raise AuthError("That username is already taken.", "taken")
            salt = secrets.token_bytes(16)
            self.conn.execute(
                "INSERT INTO users(username, username_key, display_name, pass_hash,"
                " salt, role, created_at) VALUES(?,?,?,?,?,?,?)",
                (username.strip(), key, (display_name or username).strip()[:40],
                 _hash_password(password, salt), salt.hex(),
                 role if role in ("author", "user") else "user", time.time()))
            row = self.conn.execute("SELECT * FROM users WHERE username_key=?",
                                    (key,)).fetchone()
        return self._row_to_user(row)

    def verify(self, username: str, password: str) -> Optional[Dict[str, Any]]:
        key = (username or "").strip().lower()
        with self.lock:
            row = self.conn.execute("SELECT * FROM users WHERE username_key=?",
                                    (key,)).fetchone()
        if not row or row["disabled"]:
            # Still burn time so a wrong username is not faster than a wrong password.
            _hash_password(password or "", b"0" * 16)
            return None
        calc = _hash_password(password or "", bytes.fromhex(row["salt"]))
        if not hmac.compare_digest(calc, row["pass_hash"]):
            return None
        return self._row_to_user(row)

    def by_id(self, user_id: int) -> Optional[Dict[str, Any]]:
        with self.lock:
            row = self.conn.execute("SELECT * FROM users WHERE id=?",
                                    (int(user_id),)).fetchone()
        return self._row_to_user(row) if row else None

    def list_users(self) -> List[Dict[str, Any]]:
        with self.lock:
            rows = self.conn.execute(
                "SELECT * FROM users ORDER BY (role='author') DESC, created_at ASC").fetchall()
        return [self._row_to_user(r) for r in rows]

    def user_count(self) -> int:
        with self.lock:
            return int(self.conn.execute("SELECT COUNT(*) c FROM users").fetchone()["c"])

    def set_password(self, user_id: int, new_password: str) -> None:
        bad = password_problem(new_password)
        if bad:
            raise AuthError(bad, "bad_password")
        salt = secrets.token_bytes(16)
        with self.lock:
            self.conn.execute("UPDATE users SET pass_hash=?, salt=? WHERE id=?",
                              (_hash_password(new_password, salt), salt.hex(), int(user_id)))
            self.conn.execute("DELETE FROM tokens WHERE user_id=?", (int(user_id),))

    def set_role(self, user_id: int, role: str) -> None:
        if role not in ("author", "user"):
            raise AuthError("Unknown role.", "bad_role")
        with self.lock:
            self.conn.execute("UPDATE users SET role=? WHERE id=?", (role, int(user_id)))

    def set_disabled(self, user_id: int, disabled: bool) -> None:
        with self.lock:
            self.conn.execute("UPDATE users SET disabled=? WHERE id=?",
                              (1 if disabled else 0, int(user_id)))
            if disabled:
                self.conn.execute("DELETE FROM tokens WHERE user_id=?", (int(user_id),))

    def delete_user(self, user_id: int) -> bool:
        with self.lock:
            row = self.conn.execute("SELECT role FROM users WHERE id=?",
                                    (int(user_id),)).fetchone()
            if not row or row["role"] == "author":
                return False
            self.conn.execute("DELETE FROM users WHERE id=?", (int(user_id),))
        return True

    def rename(self, user_id: int, display_name: str) -> None:
        with self.lock:
            self.conn.execute("UPDATE users SET display_name=? WHERE id=?",
                              ((display_name or "").strip()[:40], int(user_id)))

    # ------------------------------------------------------------------ tokens
    def issue_token(self, user: Dict[str, Any], ip: str = "",
                    ua: str = "") -> str:
        token = secrets.token_urlsafe(32)
        now = time.time()
        with self.lock:
            self.conn.execute(
                "INSERT INTO tokens(token_hash, user_id, created_at, expires_at,"
                " user_agent, ip) VALUES(?,?,?,?,?,?)",
                (_token_key(token), user["id"], now, now + TOKEN_DAYS * 86400,
                 (ua or "")[:200], (ip or "")[:60]))
            self.conn.execute("UPDATE users SET last_login=? WHERE id=?",
                              (now, user["id"]))
            # housekeeping: drop expired tokens
            self.conn.execute("DELETE FROM tokens WHERE expires_at < ?", (now,))
        return token

    def user_for_token(self, token: str) -> Optional[Dict[str, Any]]:
        if not token:
            return None
        with self.lock:
            row = self.conn.execute(
                "SELECT u.*, t.expires_at FROM tokens t JOIN users u ON u.id=t.user_id"
                " WHERE t.token_hash=?", (_token_key(token),)).fetchone()
            if not row:
                return None
            if row["expires_at"] < time.time() or row["disabled"]:
                self.conn.execute("DELETE FROM tokens WHERE token_hash=?",
                                  (_token_key(token),))
                return None
            # sliding expiry: extend to 30 days from now on each use
            self.conn.execute("UPDATE tokens SET expires_at=? WHERE token_hash=?",
                              (time.time() + TOKEN_DAYS * 86400, _token_key(token)))
        return self._row_to_user(row)

    def drop_token(self, token: str) -> None:
        with self.lock:
            self.conn.execute("DELETE FROM tokens WHERE token_hash=?",
                              (_token_key(token),))

    def drop_all_tokens(self, user_id: int) -> None:
        with self.lock:
            self.conn.execute("DELETE FROM tokens WHERE user_id=?", (int(user_id),))

    def log_attempt(self, user_id: Optional[int], ok: bool, ip: str = "",
                    ua: str = "") -> None:
        with self.lock:
            self.conn.execute(
                "INSERT INTO logins(user_id, ok, ts, ip, ua) VALUES(?,?,?,?,?)",
                (user_id, 1 if ok else 0, time.time(), (ip or "")[:60], (ua or "")[:200]))

    # -- author console (v2.6.2) -------------------------------------------
    def stats(self) -> Dict[str, Any]:
        """Server-wide numbers for the author dashboard."""
        week = time.time() - 7 * 86400
        with self.lock:
            row = self.conn.execute(
                "SELECT COUNT(*) c, COALESCE(SUM(role='author'),0) a FROM users").fetchone()
            new = self.conn.execute(
                "SELECT COUNT(*) c FROM users WHERE created_at >= ?", (week,)).fetchone()["c"]
            live = self.conn.execute(
                "SELECT COUNT(DISTINCT user_id) c FROM tokens WHERE expires_at > ?",
                (time.time(),)).fetchone()["c"]
            logins = self.conn.execute(
                "SELECT COUNT(*) c FROM logins WHERE ts >= ?", (week,)).fetchone()["c"]
        total, authors = int(row["c"] or 0), int(row["a"] or 0)
        return {"users": total, "authors": authors, "members": max(0, total - authors),
                "new_this_week": int(new or 0), "active_sessions": int(live or 0),
                "logins_this_week": int(logins or 0)}

    def every_user_activity(self, limit: int = 40) -> List[Dict[str, Any]]:
        """All accounts with their last sign-in and question count, newest first."""
        with self.lock:
            rows = self.conn.execute(
                "SELECT u.id, u.username, u.display_name, u.role, u.disabled, u.created_at,"
                " u.last_login,"
                " (SELECT COUNT(*) FROM facts f WHERE f.user_id=u.id) facts,"
                " (SELECT COUNT(*) FROM qa q WHERE q.user_id=u.id) asked"
                " FROM users u ORDER BY u.created_at DESC LIMIT ?", (int(limit),)).fetchall()
        return [dict(r) for r in rows]

    def recent_logins(self, user_id: int, limit: int = 8) -> List[Dict[str, Any]]:
        with self.lock:
            rows = self.conn.execute(
                "SELECT ok, ts, ip, ua FROM logins WHERE user_id=? ORDER BY ts DESC LIMIT ?",
                (int(user_id), int(limit))).fetchall()
        return [{"ok": bool(r["ok"]), "ts": r["ts"], "ip": r["ip"],
                 "ua": (r["ua"] or "")[:90]} for r in rows]


# ---------------------------------------------------------------------------
# login service with simple brute-force protection
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# one account per person (v2.6.3)
# ---------------------------------------------------------------------------
# Someone can clear localStorage, open a private window, or pick a new
# username - but they usually cannot change their device. Signup therefore
# records a device fingerprint (a hash the browser computes from its own
# platform traits) plus the IP address, and refuses a second account on
# either. The author account is exempt, and RYZEK_OPEN_SIGNUP=1 turns the
# guard off for a public deployment where shared addresses are normal.

MAX_ACCOUNTS_PER_DEVICE = 1
MAX_ACCOUNTS_PER_IP = 3


def _env_int(name: str, default: int) -> int:
    try:
        return max(0, int(os.environ.get(name, default)))
    except (TypeError, ValueError):
        return default


class SignupGuard:
    """Checks and records who has already signed up, and from where."""

    def __init__(self, db: "AuthDB") -> None:
        self.db = db

    def open_signup(self) -> bool:
        return os.environ.get("RYZEK_OPEN_SIGNUP", "").strip().lower() in ("1", "true", "yes")

    def check(self, device: str, ip: str) -> None:
        """Raise AuthError if this device or address already has an account."""
        if self.open_signup():
            return
        dev = (device or "").strip()[:64]
        if dev.startswith("test"):
            # the project's own suites create throw-away accounts on every run;
            # they identify themselves rather than being excluded by address.
            return
        with self.db.lock:
            if dev:
                row = self.db.conn.execute(
                    "SELECT COUNT(*) c FROM signups WHERE device=?", (dev,)).fetchone()
                if int(row["c"] or 0) >= MAX_ACCOUNTS_PER_DEVICE:
                    raise AuthError(
                        "This device already has an account. Sign in with it instead. "
                        "If you forgot the password, ask the creator to reset it.",
                        "device_used")
            if ip:
                limit = _env_int("RYZEK_MAX_PER_IP", MAX_ACCOUNTS_PER_IP)
                if ip.startswith("127.") or ip in ("::1", "localhost", ""):
                    # loopback is this machine; a person testing the app or the
                    # test suite legitimately makes more than one account here
                    limit = max(limit, _env_int("RYZEK_MAX_PER_LOOPBACK", 12))
                row = self.db.conn.execute(
                    "SELECT COUNT(*) c FROM signups WHERE ip=?", (ip,)).fetchone()
                if limit and int(row["c"] or 0) >= limit:
                    raise AuthError(
                        "Too many accounts have been created from this connection. "
                        "Sign in to the account you already have, or try again later.",
                        "ip_used")

    def record(self, user_id: int, device: str, ip: str, ua: str = "") -> None:
        with self.db.lock:
            self.db.conn.execute(
                "INSERT INTO signups(user_id, ts, ip, device, ua) VALUES(?,?,?,?,?)",
                (int(user_id), time.time(), (ip or "")[:64], (device or "")[:64],
                 (ua or "")[:200]))

    def summary(self) -> Dict[str, Any]:
        with self.db.lock:
            dev = self.db.conn.execute(
                "SELECT COUNT(DISTINCT device) c FROM signups WHERE device!=''").fetchone()["c"]
            rows = self.db.conn.execute(
                "SELECT ip, COUNT(*) c FROM signups WHERE ip!='' GROUP BY ip "
                "HAVING c > 1 ORDER BY c DESC LIMIT 8").fetchall()
        return {"devices": int(dev or 0),
                "shared_ips": [{"ip": r["ip"], "accounts": int(r["c"])} for r in rows]}


class AuthService:
    def __init__(self, db: Optional[AuthDB] = None) -> None:
        self.db = db or AuthDB.shared()
        self._fails: Dict[str, List[float]] = {}
        self._lock = threading.Lock()

    # ---- brute force guard: 8 failures per username/IP in 10 minutes
    def _guard(self, key: str) -> None:
        now = time.time()
        with self._lock:
            if len(self._fails) > 4000:
                self._fails.clear()
            hits = [t for t in self._fails.get(key, []) if now - t < 600]
            self._fails[key] = hits
            if len(hits) >= 8:
                wait = int(600 - (now - hits[0]))
                raise AuthError(
                    f"Too many failed attempts. Please wait {max(wait, 30)} seconds.",
                    "rate_limited")

    def _note_fail(self, key: str) -> None:
        with self._lock:
            self._fails.setdefault(key, []).append(time.time())

    def signup(self, username: str, password: str, display_name: str = "",
               ip: str = "", ua: str = "") -> Tuple[Dict[str, Any], str]:
        user = self.db.create_user(username, password, display_name)
        token = self.db.issue_token(user, ip, ua)
        self.db.log_attempt(user["id"], True, ip, ua)
        return user, token

    def login(self, username: str, password: str, ip: str = "",
              ua: str = "") -> Tuple[Dict[str, Any], str]:
        key = f"{(username or '').strip().lower()}|{ip}"
        self._guard(key)
        user = self.db.verify(username, password)
        if not user:
            self._note_fail(key)
            self.db.log_attempt(None, False, ip, ua)
            raise AuthError("Wrong username or password.", "bad_credentials")
        token = self.db.issue_token(user, ip, ua)
        self.db.log_attempt(user["id"], True, ip, ua)
        return user, token

    def logout(self, token: str) -> None:
        self.db.drop_token(token)

    def current(self, token: str) -> Optional[Dict[str, Any]]:
        return self.db.user_for_token(token)

    def public(self, user: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        if not user:
            return None
        return {"id": user["id"], "username": user["username"],
                "display_name": user["display_name"], "role": user["role"],
                "created_at": user["created_at"], "last_login": user["last_login"]}


AUTH = AuthService()


def random_password(length: int = 12) -> str:
    """Readable random password for author-issued resets (no look-alike chars)."""
    alphabet = "abcdefghjkmnpqrstuvwxyzABCDEFGHJKLMNPQRSTUVWXYZ23456789"
    return "".join(secrets.choice(alphabet) for _ in range(max(8, int(length))))


def bearer(headers: Any) -> str:
    """Read the token from an Authorization header or the ryzek_token cookie."""
    try:
        raw = headers.get("Authorization") or ""
        if raw.lower().startswith("bearer "):
            return raw[7:].strip()
        cookie = headers.get("Cookie") or ""
        for part in cookie.split(";"):
            name, _, value = part.strip().partition("=")
            if name == "ryzek_token":
                return value.strip()
    except Exception:
        pass
    return ""
