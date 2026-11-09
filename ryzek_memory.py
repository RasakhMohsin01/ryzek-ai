#!/usr/bin/env python3
"""
Ryzek AI v2.6 - what Ryzek remembers, per account.

Two kinds of memory:

    facts   durable things about the person and their world
            ("my name is Ali", "I live in Lahore", "my goal is to learn Python")
    qa      every question they asked and a summary of the answer, so
            "what did I ask you earlier?" and "what was that about capacitors?"
            both work.

Storage: the `facts` and `qa` tables in data/ryzek.db (created by ryzek_auth).
When no database is available the same class falls back to a JSON file, so the
engine still works if someone deletes the database or runs on a read-only disk.
"""

from __future__ import annotations

import json
import os
import re
import threading
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import ryzek_understand as understand

ROOT = Path(__file__).resolve().parent
DATA_DIR = Path(os.environ.get("RYZEK_DATA") or (ROOT / "data"))
JSON_PATH = DATA_DIR / "memory.json"

MAX_FACTS = 400
MAX_QA = 5000

# Sentences worth remembering, with the key they are stored under.
_RULES: List[Tuple[str, str]] = [
    (r"\bmy name is\b", "name"),
    (r"\bcall me\b", "name"),
    (r"\bi am ([A-Z][\w' -]{1,28})(?:,|\.|$|\s+from\b|\s+who\b)", "name"),   # only capitalised names
    (r"\bi'?m ([A-Z][\w' -]{1,28})(?:,|\.|$)", "name"),
    (r"\bi work as (?:a|an)?\s*([\w '+-]{2,40})", "job"),
    (r"\bi am (?:a|an) ([\w '+-]{2,40}?) (?:by profession|and i work)", "job"),
    (r"\bi live in ([\w '.,-]{2,40})", "city"),
    (r"\bi am from ([\w '.,-]{2,40})", "city"),
    (r"\bi study (?:at|in) ([\w '.,-]{2,40})", "school"),
    (r"\bmy (?:goal|aim|target) is (?:to )?([\w '.,!+-]{2,80})", "goal"),
    (r"\bi want to (?:learn|become|build) ([\w '.,!+-]{2,80})", "goal"),
    (r"\bmy favou?rite ([\w ]{2,20}?)\s+is\s+([\w '.,+-]{2,40})", "favourite"),
    (r"\bmy favou?rite ([\w ]{2,20}?)\s*[:\-]\s*([\w '.,+-]{2,40})", "favourite"),
    (r"\bi (?:like|love|enjoy) ([\w '.,+-]{2,60})", "likes"),
    (r"\bi (?:hate|dislike|can't stand) ([\w '.,+-]{2,60})", "dislikes"),
    (r"\bi speak ([\w '.,+-]{2,40})", "language"),
    (r"\bmy birthday is ([\w '.,/-]{2,30})", "birthday"),
    (r"\bmy (?:phone|laptop|computer) is (?:a|an)?\s*([\w '.,+-]{2,40})", "device"),
]


class RyzekMemory:
    """Per-user long-term memory. Thread-safe; falls back to JSON."""

    def __init__(self, db=None, path: Path = JSON_PATH) -> None:
        self.db = db
        self.path = Path(path)
        self.lock = threading.RLock()
        if self.db is None:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            if not self.path.exists():
                self.path.write_text(json.dumps({"facts": {}, "qa": []}),
                                     encoding="utf-8")

    # ---------------------------------------------------------------- writing
    def _user(self, user_id: Optional[int]) -> Optional[int]:
        """Database-backed memory is per real account. Guest memory (user 0)
        would violate the users foreign key, so with SQLite we simply do not
        store guest facts - the session object still carries them."""
        if not user_id:
            return None if self.db is not None else 0
        return int(user_id)

    def _rows(self, sql: str, args: tuple):
        """Run a query for the current user, tolerating the guest case."""
        uid = self._user(args[0] if args else None)
        if uid is None:
            return []
        return self.db.conn.execute(sql, (uid,) + tuple(args[1:])).fetchall()

    def _exec(self, sql: str, args: tuple) -> None:
        uid = self._user(args[0] if args else None)
        if uid is None:
            return
        self.db.conn.execute(sql, (uid,) + tuple(args[1:]))

    def remember_fact(self, user_id: Optional[int], key: str, value: str,
                      source: str = "") -> None:
        key = re.sub(r"[^a-z0-9_]+", "_", (key or "").strip().lower())[:40]
        value = re.sub(r"\s+", " ", (value or "").strip())[:220]
        if not key or not value:
            return
        now = time.time()
        if self.db is not None:
            with self.db.lock:
                self._exec(
                    "INSERT INTO facts(user_id, key, value, source, created_at, updated_at)"
                    " VALUES(?,?,?,?,?,?) ON CONFLICT(user_id, key) DO UPDATE SET"
                    " value=excluded.value, source=excluded.source, updated_at=excluded.updated_at",
                    (user_id, key, value, source[:60], now, now))
            return
        with self.lock:
            data = self._load_json()
            bucket = data["facts"].setdefault(str(self._user(user_id)), {})
            bucket[key] = {"value": value, "source": source, "at": now}
            self._save_json(data)

    def get_fact(self, user_id: Optional[int], key: str) -> Optional[str]:
        key = re.sub(r"[^a-z0-9_]+", "_", (key or "").strip().lower())
        if self.db is not None:
            with self.db.lock:
                rows = self._rows("SELECT value FROM facts WHERE user_id=? AND key=?",
                                  (user_id, key))
            return rows[0]["value"] if rows else None
        with self.lock:
            data = self._load_json()
            item = data["facts"].get(str(self._user(user_id)), {}).get(key)
            return item["value"] if item else None

    def all_facts(self, user_id: Optional[int], limit: int = 30) -> List[Dict[str, Any]]:
        if self.db is not None:
            with self.db.lock:
                rows = self._rows(
                    "SELECT key, value, updated_at FROM facts WHERE user_id=?"
                    " ORDER BY updated_at DESC LIMIT ?", (user_id, limit))
            return [{"key": r["key"], "value": r["value"], "at": r["updated_at"]}
                    for r in rows]
        with self.lock:
            data = self._load_json()
            items = data["facts"].get(str(self._user(user_id)), {})
        rows = [{"key": k, "value": v["value"], "at": v.get("at", 0)}
                for k, v in items.items()]
        return sorted(rows, key=lambda r: -r["at"])[:limit]

    def forget_fact(self, user_id: Optional[int], key: str) -> None:
        key = re.sub(r"[^a-z0-9_]+", "_", (key or "").strip().lower())
        if self.db is not None:
            with self.db.lock:
                self._exec("DELETE FROM facts WHERE user_id=? AND key=?", (user_id, key))
            return
        with self.lock:
            data = self._load_json()
            data["facts"].get(str(self._user(user_id)), {}).pop(key, None)
            self._save_json(data)

    def clear(self, user_id: Optional[int]) -> None:
        if self.db is not None:
            with self.db.lock:
                self._exec("DELETE FROM facts WHERE user_id=?", (user_id,))
                self._exec("DELETE FROM qa WHERE user_id=?", (user_id,))
            return
        with self.lock:
            data = self._load_json()
            data["facts"].pop(str(self._user(user_id)), None)
            data["qa"] = [r for r in data["qa"] if r.get("u") != self._user(user_id)]
            self._save_json(data)

    # -------------------------------------------------------------- questions
    def log_question(self, user_id: Optional[int], session_id: str, question: str,
                     answer: str, topic: str = "") -> None:
        question = re.sub(r"\s+", " ", question or "").strip()[:400]
        if not question:
            return
        # store a compact summary rather than the whole 20 KB answer
        summary = understand.split_sentences(re.sub(r"[#*`>_]", "", answer or ""))
        short = " ".join(summary[:3])[:500]
        now = time.time()
        if self.db is not None:
            with self.db.lock:
                self._exec(
                    "INSERT INTO qa(user_id, session_id, question, answer, topic, created_at)"
                    " VALUES(?,?,?,?,?,?)",
                    (user_id, session_id or "", question, short, (topic or "")[:80], now))
                uid = self._user(user_id)
                if uid is not None:
                    self.db.conn.execute(
                        "DELETE FROM qa WHERE user_id=? AND id NOT IN ("
                        " SELECT id FROM qa WHERE user_id=? ORDER BY id DESC LIMIT ?)",
                        (uid, uid, MAX_QA))
            return
        with self.lock:
            data = self._load_json()
            data["qa"].insert(0, {"u": self._user(user_id), "s": session_id,
                                  "q": question, "a": short, "t": topic, "at": now})
            data["qa"] = data["qa"][:MAX_QA]
            self._save_json(data)

    def recent_questions(self, user_id: Optional[int], limit: int = 8) -> List[Dict[str, Any]]:
        if self.db is not None:
            with self.db.lock:
                rows = self._rows(
                    "SELECT question, answer, topic, session_id, created_at FROM qa"
                    " WHERE user_id=? ORDER BY id DESC LIMIT ?", (user_id, int(limit)))
            return [{"question": r["question"], "answer": r["answer"],
                     "topic": r["topic"], "session_id": r["session_id"],
                     "at": r["created_at"]} for r in rows]
        with self.lock:
            data = self._load_json()
        rows = [r for r in data["qa"] if r.get("u") == self._user(user_id)]
        return [{"question": r["q"], "answer": r["a"], "topic": r.get("t", ""),
                 "session_id": r.get("s", ""), "at": r.get("at", 0)}
                for r in rows[:limit]]

    def search_questions(self, user_id: Optional[int], query: str,
                         limit: int = 5) -> List[Dict[str, Any]]:
        terms = understand.content_terms(query)
        if not terms:
            return []
        rows = self.recent_questions(user_id, limit=300)
        scored = []
        for r in rows:
            hay = (r["question"] + " " + r["answer"] + " " + r.get("topic", "")).lower()
            score = sum(1 for t in terms if t in hay)
            if score:
                scored.append((score, r))
        scored.sort(key=lambda x: -x[0])
        return [r for _, r in scored[:limit]]

    def stats(self, user_id: Optional[int]) -> Dict[str, Any]:
        if self.db is not None:
            with self.db.lock:
                f_rows = self._rows("SELECT COUNT(*) c FROM facts WHERE user_id=?",
                                    (user_id,))
                q_rows = self._rows("SELECT COUNT(*) c FROM qa WHERE user_id=?",
                                    (user_id,))
                facts = f_rows[0]["c"] if f_rows else 0
                qa = q_rows[0]["c"] if q_rows else 0
            return {"facts": int(facts), "questions": int(qa)}
        with self.lock:
            data = self._load_json()
            facts = len(data["facts"].get(str(self._user(user_id)), {}))
            qa = sum(1 for r in data["qa"] if r.get("u") == self._user(user_id))
        return {"facts": facts, "questions": qa}

    # --------------------------------------------------------------- learning
    def learn_from_message(self, user_id: Optional[int], message: str) -> List[str]:
        """Scan a user message for durable facts. Returns the keys stored."""
        stored: List[str] = []
        text = message or ""
        if len(text) < 4:
            return stored
        name = understand.find_name(text)
        if name and re.search(r"\b(my name is|call me|mera naam)\b", text, re.I):
            self.remember_fact(user_id, "name", name, "said in chat")
            stored.append("name")
        for pat, key in _RULES:
            if key == "name":
                continue
            m = re.search(pat, text, re.I)
            if not m:
                continue
            value = m.group(1).strip(" .,-")
            if not value or len(value) < 2:
                continue
            if key == "favourite":
                # "my favourite colour is blue" -> favourite_colour = blue
                sub = re.sub(r"[^a-z]+", "_", m.group(1).lower()).strip("_")
                self.remember_fact(user_id, "favourite_" + sub, value, "said in chat")
                stored.append("favourite_" + sub)
            else:
                self.remember_fact(user_id, key, value, "said in chat")
                stored.append(key)
        return stored

    # ---------------------------------------------------------------- json io
    def _load_json(self) -> Dict[str, Any]:
        try:
            return json.loads(self.path.read_text(encoding="utf-8"))
        except Exception:
            return {"facts": {}, "qa": []}

    def _save_json(self, data: Dict[str, Any]) -> None:
        tmp = self.path.with_suffix(".tmp")
        try:
            tmp.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
            os.replace(tmp, self.path)
        except Exception:
            pass


def shared_memory() -> RyzekMemory:
    """One memory object for the whole process, using the auth database."""
    global _MEMORY
    try:
        return _MEMORY
    except NameError:
        pass
    db = None
    try:
        import ryzek_auth
        db = ryzek_auth.AuthDB.shared()
    except Exception:
        db = None
    _MEMORY = RyzekMemory(db=db)
    return _MEMORY
