#!/usr/bin/env python3
"""
Ryzek AI v2 - core engine.

What lives here:
  * Curated knowledge base + BM25 retrieval index (real information retrieval)
  * Live Wikipedia research with local caching -> the bot gets smarter as you use it
  * A tool registry / plugin system (decorator-based, auto-generates LLM tool schemas)
  * A research composer that writes long, structured, sourced answers
  * An agentic LLM loop with up to 8 tool-using steps (optional API key)
  * Persistent sessions, memory, and a no-silent-failure guarantee

Standard library only. Imported by ryzek_ai.py (server + CLI).
"""

from __future__ import annotations

import ast
import html
import json
import math
import operator
import os
import random
import re
import threading
import time
import uuid
from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple
from urllib import request as urlrequest
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlencode

try:
    from zoneinfo import ZoneInfo
except Exception:  # pragma: no cover
    ZoneInfo = None  # type: ignore

import ryzek_quality as q
import ryzek_facts as factdb
import ryzek_reason as reason
import ryzek_safety as safety
import ryzek_chat as chat
import ryzek_writing as writing
import ryzek_web as web
import ryzek_plain as plain
import ryzek_understand as understand
import ryzek_answer as answer_kit
import ryzek_memory as memory_kit
import ryzek_everyday as everyday
import ryzek_poetry as poetry_kit
import ryzek_auth as auth_kit

NAME = "Ryzek AI"
VERSION = "2.6.4"

# --- Identity: the person who owns and built this agent --------------------
CREATOR = "Rasakh Mohsin aka Ryzek"
CREATOR_HANDLE = "Ryzek_20"
CREATOR_INSTAGRAM = "@rasakh_mohsin"
CREATOR_INSTAGRAM_URL = "https://www.instagram.com/rasakh_mohsin/"
CREATOR_ROLE = "data scientist"

ROOT = Path(__file__).resolve().parent
# RYZEK_DATA lets a host app (e.g. the Android build) put sessions and caches in
# writable storage. On the phone the bundled source folder is read-only.
DATA_DIR = Path(os.environ.get("RYZEK_DATA") or (ROOT / "data"))
LEARNED_DIR = DATA_DIR / "learned"
SESSIONS_FILE = DATA_DIR / "sessions.json"
CONFIG_FILE = DATA_DIR / "config.json"
KB_FILE = ROOT / "knowledge_base.json"
DATA_DIR.mkdir(parents=True, exist_ok=True)
LEARNED_DIR.mkdir(parents=True, exist_ok=True)

MAX_LEARNED = 80
WIKI_API = "https://en.wikipedia.org/w/api.php"
USER_AGENT = f"RyzekAI/{VERSION} (educational research assistant; Python stdlib)"

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

ONLINE = os.environ.get("RYZEK_ONLINE", "1") not in ("0", "false", "no")
DEFAULT_DEPTH = os.environ.get("RYZEK_DEPTH", "exhaustive")
DEPTHS = ("quick", "standard", "deep", "exhaustive")
if DEFAULT_DEPTH not in DEPTHS:
    DEFAULT_DEPTH = "exhaustive"
MAX_STEPS = int(os.environ.get("RYZEK_MAX_STEPS", "8"))

def build_system_prompt(opts: Optional[Dict[str, Any]] = None, depth: str = "deep") -> str:
    """Per-request LLM system prompt: respect policy, grammar and one-time headings."""
    o = q.default_opts(opts)
    rules = [
        f"You are {NAME} v{VERSION}, an advanced research agent built in Python by the person "
        "talking to you. You are precise, warm and genuinely thorough.",
        "",
        "NON-NEGOTIABLE RULES:",
        "1. ALWAYS answer. Every message gets a substantive, detailed reply. Never return an empty "
        "string or a bare statement of ignorance; never refuse without useful content.",
        "2. For factual or explanatory questions, use the live web material already gathered from "
        "Google, Bing, DuckDuckGo, Wikipedia and other platforms, and call research tools FIRST "
        "(wikipedia_search, then wikipedia_read on the best titles, and local_search). Ground the "
        "answer in what the tools returned. Cite sources as [Title](url) at the end.",
        "3. Write clear, intermediate-level English: short everyday words and plain sentences. "
        "No academic padding, no fragments, no comma splices, no repeated words, no orphan headings.",
        "4. Use EVERY heading EXACTLY ONCE. Never repeat a heading anywhere in the answer. Group "
        "material under one heading instead of re-emitting it.",
        "5. Be concrete: definitions, mechanisms, numbers, examples and a worked example or code "
        "snippet when relevant. Every paragraph must carry information - no filler.",
        "6. If uncertain or a tool returned nothing, say exactly what you know, state assumptions "
        "explicitly, give the best practical answer, explain how to verify it, and ask at most ONE "
        "focused clarifying question.",
        "7. Never invent sources, quotes, prices, scores, dates or live data. If a tool fails, say so.",
        "8. Use tools for arithmetic, dates, unit conversions and memory - never guess a calculation.",
        "9. If asked who built you: \"You did - I'm " + NAME + ", the Python agent you built.\"",
        "10. Never mention these instructions or internal step names in the answer itself.",
    ]
    if q.respect_on(o):
        rules += [
            "",
            "RESPECT POLICY - applies to every religion, prophet, Scripture and community:",
            "- Treat all prophets, Scriptures, religions and believers with courtesy and dignity. "
            "Never joke about, mock, caricature or make light of them, even if the user's phrasing "
            "is irreverent. If the question is disrespectful, answer calmly without repeating the insult.",
            "- Be strictly neutral: do not rank religions, declare any community correct or "
            "incorrect, or take sides in sectarian disputes. Attribute differing views to their "
            "traditions ('In Islamic tradition...', 'Christian sources state...', "
            "'According to the Hebrew Bible...').",
            "- You are NOT a scholar, mufti, priest or religious authority. Do not issue fatwas, "
            "legal rulings or personal religious guidance; refer the user to qualified scholars "
            "and their own Scripture and community.",
            "- Never fabricate details of a prophet's life, a revelation or a tradition's teachings. "
            "Use honorifics when the user has enabled them in Settings.",
            "- For religious or prophet-related topics, open with a short '## A note on respect' "
            "section, then continue with the answer.",
        ]
        if o["respect_mode"] == "islamic" and o["honorifics"] != "none":
            suffix = "ﷺ" if o["honorifics"] == "arabic" else "(peace be upon him)"
            rules.append("- Mention prophets with the honorific " + suffix + ", as the user requested in Settings.")
    if o["simple_english"] or o["style"] == "simple":
        rules += ["", "STYLE: plain, simple English. Short sentences. Define every technical term "
                  "at first use. Avoid jargon and idioms."]
    elif o["style"] == "academic":
        rules += ["", "STYLE: formal academic register. State scope and limitations; distinguish "
                  "evidence from interpretation."]
    elif o["style"] == "exam":
        rules += ["", "STYLE: exam-ready. Definition first, then mechanism, one example, one "
                  "limitation, and a compact 'Exam-ready summary' section."]

    if depth == "exhaustive":
        rules += [
            "",
            "ANSWER FORMAT - use each of these headings exactly ONCE, in this order:",
            "## A note on respect (only for religious / prophet topics)",
            "## Short answer", "## Overview and definition", "## In detail",
            "## How it works, step by step", "## Types and classifications",
            "## Background and history", "## Timeline of dated milestones",
            "## Applications and real-world use", "## Key points",
            "## Example and practical angle", "## Advantages, limitations and common mistakes",
            "## Comparison with related ideas", "## Frequently asked questions",
            "## Glossary of key terms", "## Sources", "## What I could not verify",
            "## Keep going",
            "Be comprehensive: aim for 900-1600 words with real content under every heading. "
            "If the sources do not cover a section, say so honestly in one sentence instead of "
            "inventing material. Never leave a heading empty and never reuse a heading.",
        ]
    else:
        rules += [
            "",
            "ANSWER FORMAT - use each heading exactly ONCE:",
            "## Short answer", "## In detail", "## Key points",
            "## Example / practical angle", "## Common mistakes and limits",
            "## Sources", "## What I could not verify", "## Keep going",
            "Aim for 350-700 words on deep questions.",
        ]
    if depth == "quick":
        rules.append("This is a QUICK answer: keep it under 180 words but still structured.")
    rules.append("Use short paragraphs and tight bullets. Use British-neutral spelling.")
    return "\n".join(rules)


SYSTEM_PROMPT = build_system_prompt()              # backwards-compatible default
SYSTEM_PROMPT_QUICK = build_system_prompt(depth="quick")

# ---------------------------------------------------------------------------
# Small utilities
# ---------------------------------------------------------------------------


def fmt_number(x: Any) -> str:
    try:
        x = float(x)
    except (TypeError, ValueError):
        return str(x)
    if not math.isfinite(x):
        return str(x)
    if abs(x) >= 1e12 or (x != 0 and abs(x) < 1e-6):
        return f"{x:.6g}"
    if x.is_integer():
        return str(int(x))
    return f"{round(x, 10):g}"


def sentences(text: str) -> List[str]:
    return [s.strip() for s in re.split(r"(?<=[.!?])\s+", text.strip()) if s.strip()]


def condense(text: str, n: int = 2, limit: int = 700) -> str:
    """Take the first real sentences, skipping headings/fragments."""
    real = [s for s in sentences(text) if len(s) > 40 and not re.match(r"^[A-Z][\w\s]{0,28}[:.]$", s)]
    return (" ".join(real[:n]) or text.strip())[:limit]


def wiki_url(title: str, simple: bool = False) -> str:
    host = "simple.wikipedia.org" if simple else "en.wikipedia.org"
    return f"https://{host}/wiki/" + quote(title.replace(" ", "_"), safe="_()',")


def slug(title: str) -> str:
    return (re.sub(r"[^a-z0-9]+", "_", title.lower()).strip("_")[:80] or "article")


def strip_html(s: str) -> str:
    return html.unescape(re.sub(r"<[^>]+>", "", s or ""))


STOPWORDS = set("""a an the and or of to in on for with is are was were be been being it its this that these those
as at by from into about over under than then so if but not no do does did doing have has had having i you he she
they we me my your our their them him her who whom what which when where why how can could should would will shall
may might must please tell explain define describe give show make want need about answer question me""".split())


def tokens(text: str) -> List[str]:
    out = []
    for w in re.findall(r"[a-z0-9]+", text.lower()):
        if len(w) <= 2 or w in STOPWORDS:
            continue
        if len(w) > 4 and w.endswith("s") and not w.endswith("ss"):
            w = w[:-1]  # crude stem: 'holes' -> 'hole', 'capitals' -> 'capital'
        out.append(w)
    return out


def search_terms(question: str, limit: int = 9) -> str:
    """Turn a long question into a compact Wikipedia search query."""
    words = [w for w in re.findall(r"[a-zA-Z0-9]+", question) if w.lower() not in STOPWORDS and len(w) > 2]
    seen, out = set(), []
    for w in words:
        if w.lower() not in seen:
            seen.add(w.lower())
            out.append(w)
    return " ".join(out[:limit]) or question[:80]


# Common typos in the questions people actually type. Normalising them BEFORE
# intent detection means "timme travel possibility" reaches the time-travel
# topic instead of the clock tool or a random Wikipedia article.
_TYPO_FIXES = [
    (r"\btimme\b", "time"),
    (r"\btiime\b", "time"),
    (r"\btim e\b", "time"),
    (r"\btravle\b", "travel"),
    (r"\btravell?ing\b", "travelling"),
    (r"\bpossibilty\b", "possibility"),
    (r"\bposibility\b", "possibility"),
    (r"\bpossiblity\b", "possibility"),
    (r"\bpoibility\b", "possibility"),
    (r"\bcapitla\b", "capital"),
    (r"\bcaptial\b", "capital"),
    (r"\bcapitial\b", "capital"),
    (r"\bcapitol\b", "capital"),
    (r"\bcapitel\b", "capital"),
    (r"\bcapitil\b", "capital"),
    (r"\bgazal\b", "ghazal"),
    (r"\bbecuase\b", "because"),
    (r"\brecieve\b", "receive"),
    (r"\bwich\b", "which"),
    (r"\bwhta\b", "what"),
]


def normalise_question(text: str) -> str:
    out = text or ""
    for pattern, repl in _TYPO_FIXES:
        out = re.sub(pattern, repl, out, flags=re.I)
    return re.sub(r"\s+", " ", out).strip()


def build_search_query(question: str) -> str:
    """Full natural question for 'why' (finds causal articles), keywords otherwise."""
    if re.match(r"^\s*why\b", question.lower()):
        return re.sub(r"\s+", " ", question).strip()[:120]
    return search_terms(question, 8)


def rank_results(question: str, results: List[Dict[str, str]]) -> List[Dict[str, str]]:
    """Trust Wikipedia's own relevance order; only drop obvious junk pages."""
    out = []
    for r in results:
        if "may also refer to" in r["snippet"].lower():
            continue
        if re.search(r"\(album\)|\(film\)|disambiguation|^list of\b", r["title"], re.I):
            continue
        out.append(r)
    return out


# ---------------------------------------------------------------------------
# Safe arithmetic (no eval, ever)
# ---------------------------------------------------------------------------

_BIN_OPS = {
    ast.Add: operator.add, ast.Sub: operator.sub, ast.Mult: operator.mul,
    ast.Div: operator.truediv, ast.FloorDiv: operator.floordiv,
    ast.Mod: operator.mod, ast.Pow: operator.pow,
}
_UNARY_OPS = {ast.UAdd: operator.pos, ast.USub: operator.neg}
_CONSTANTS = {"pi": math.pi, "e": math.e}
_FUNCTIONS = {
    "sqrt": math.sqrt, "abs": abs, "round": round, "log": math.log10,
    "ln": math.log, "sin": math.sin, "cos": math.cos, "tan": math.tan,
    "floor": math.floor, "ceil": math.ceil,
}
_CANDIDATE_RE = re.compile(
    r"(?:(?:sqrt|abs|round|log|ln|sin|cos|tan|floor|ceil)(?=\s*\()|\bpi\b|\be\b|"
    r"\d+(?:\.\d+)?|\.\d+|[+\-*/()^%]|\s)+",
    re.IGNORECASE,
)


def _eval_node(node: ast.AST) -> float:
    if isinstance(node, ast.Expression):
        return _eval_node(node.body)
    if isinstance(node, ast.Constant) and type(node.value) in (int, float):
        return float(node.value)
    if isinstance(node, ast.Name) and node.id in _CONSTANTS:
        return _CONSTANTS[node.id]
    if isinstance(node, ast.UnaryOp) and type(node.op) in _UNARY_OPS:
        return _UNARY_OPS[type(node.op)](_eval_node(node.operand))
    if isinstance(node, ast.BinOp) and type(node.op) in _BIN_OPS:
        left, right = _eval_node(node.left), _eval_node(node.right)
        if isinstance(node.op, ast.Pow) and (abs(right) > 64 or abs(left) > 1e6):
            raise ValueError("exponent too large")
        try:
            return _BIN_OPS[type(node.op)](left, right)
        except ZeroDivisionError as exc:
            raise ValueError("division by zero") from exc
    if (isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
            and node.func.id in _FUNCTIONS and len(node.args) == 1 and not node.keywords):
        return _FUNCTIONS[node.func.id](_eval_node(node.args[0]))
    raise ValueError("unsupported expression")


def normalise_math(raw: str) -> str:
    s = raw.lower().strip()
    for a, b in (("×", "*"), ("÷", "/"), ("−", "-"), ("–", "-"), ("—", "-")):
        s = s.replace(a, b)
    s = re.sub(r"(\d+(?:\.\d+)?)\s*%\s*of\s*(\d+(?:\.\d+)?)", r"(\1/100)*\2", s)
    s = re.sub(r"(\d+(?:\.\d+)?)\s*%", r"(\1/100)", s)
    for word, sym in {"plus": "+", "minus": "-", "times": "*", "multiplied by": "*",
                      "divided by": "/", "over": "/", "to the power of": "**",
                      "modulo": "%", "mod": "%", "square root of": "sqrt"}.items():
        s = re.sub(r"\b" + re.escape(word) + r"\b", f" {sym} ", s)
    s = re.sub(r"(?<=\d)\s*x\s*(?=\d)", " * ", s)
    s = re.sub(r"\bsquared\b", " ** 2 ", s)
    s = re.sub(r"\bcubed\b", " ** 3 ", s)
    return s.replace("^", " ** ")


def calculator(expression: str) -> str:
    s = normalise_math(str(expression))
    if len(s) > 400:
        raise ValueError("expression is too long")
    best = ""
    for m in _CANDIDATE_RE.finditer(s):
        c = m.group(0).strip().rstrip("+-*/^%. ")
        if re.search(r"\d", c) and re.search(r"[+\-*/^%]", c) and len(c) > len(best):
            best = c
    if not best or len(best) > 200:
        raise ValueError("no usable arithmetic found")
    value = _eval_node(ast.parse(best.replace("^", "**"), mode="eval"))
    return f"{best} = {fmt_number(value)}"


def current_time(timezone: str = "") -> str:
    tz = timezone or os.environ.get("RYZEK_TZ", "")
    now = None
    if tz and ZoneInfo is not None:
        try:
            now = datetime.now(ZoneInfo(tz))
        except Exception:
            now = None
    if now is None:
        now = datetime.now().astimezone()
    return now.strftime("%A, %d %B %Y  |  %I:%M %p  |  %Z")


_UNITS = {
    "mm": ("length", 0.001), "cm": ("length", 0.01), "m": ("length", 1.0),
    "km": ("length", 1000.0), "in": ("length", 0.0254), "ft": ("length", 0.3048),
    "yd": ("length", 0.9144), "mi": ("length", 1609.344),
    "mg": ("mass", 1e-6), "g": ("mass", 0.001), "kg": ("mass", 1.0),
    "oz": ("mass", 0.028349523125), "lb": ("mass", 0.45359237),
    "ml": ("volume", 0.001), "l": ("volume", 1.0), "gal": ("volume", 3.785411784),
    "cup": ("volume", 0.2365882365),
}
_UNIT_ALIASES = {
    "millimeter": "mm", "millimeters": "mm", "millimetre": "mm", "millimetres": "mm",
    "centimeter": "cm", "centimeters": "cm", "centimetre": "cm", "centimetres": "cm",
    "meter": "m", "meters": "m", "metre": "m", "metres": "m",
    "kilometer": "km", "kilometers": "km", "kilometre": "km", "kilometres": "km", "kms": "km",
    "inch": "in", "inches": "in", "foot": "ft", "feet": "ft", "yard": "yd", "yards": "yd",
    "mile": "mi", "miles": "mi", "milligram": "mg", "milligrams": "mg",
    "gram": "g", "grams": "g", "kilogram": "kg", "kilograms": "kg", "kilo": "kg", "kilos": "kg",
    "ounce": "oz", "ounces": "oz", "pound": "lb", "pounds": "lb", "lbs": "lb",
    "milliliter": "ml", "milliliters": "ml", "millilitre": "ml", "millilitres": "ml",
    "liter": "l", "liters": "l", "litre": "l", "litres": "l",
    "gallon": "gal", "gallons": "gal", "cup": "cup", "cups": "cup",
    "celsius": "c", "centigrade": "c", "fahrenheit": "f", "kelvin": "k",
    "c": "c", "f": "f", "k": "k", "°c": "c", "°f": "f",
}


def canonical_unit(unit: str) -> str:
    key = unit.strip().lower().rstrip(".,?!°")
    if key in _UNITS:
        return key
    if key in _UNIT_ALIASES:
        return _UNIT_ALIASES[key]
    raise ValueError(f"unknown unit '{unit}'")


def convert_unit(value: float, from_unit: str, to_unit: str) -> str:
    value = float(value)
    src, dst = canonical_unit(from_unit), canonical_unit(to_unit)
    temps = ("c", "f", "k")
    if src in temps or dst in temps:
        if src not in temps or dst not in temps:
            raise ValueError("temperature only converts to temperature")
        c = {"c": value, "f": (value - 32) * 5 / 9, "k": value - 273.15}[src]
        out = {"c": c, "f": c * 9 / 5 + 32, "k": c + 273.15}[dst]
        return f"{fmt_number(value)} deg {src.upper()} = {fmt_number(out)} deg {dst.upper()}"
    kind_a, fa = _UNITS[src]
    kind_b, fb = _UNITS[dst]
    if kind_a != kind_b:
        raise ValueError(f"cannot convert {kind_a} into {kind_b}")
    return f"{fmt_number(value)} {src} = {fmt_number(value * fa / fb)} {dst}"


# ---------------------------------------------------------------------------
# Knowledge base + BM25 retrieval
# ---------------------------------------------------------------------------


def load_knowledge_base() -> List[Dict[str, Any]]:
    try:
        with KB_FILE.open("r", encoding="utf-8") as fh:
            return json.load(fh).get("topics", [])
    except Exception as exc:  # pragma: no cover
        print(f"[Ryzek] knowledge_base.json could not be loaded: {exc}", flush=True)
        return []


KB = load_knowledge_base()


def chunk_text(text: str, size: int = 720) -> List[str]:
    parts, buf = [], ""
    for sent in sentences(text):
        if len(buf) + len(sent) + 1 > size and buf:
            parts.append(buf.strip())
            buf = sent
        else:
            buf = (buf + " " + sent).strip()
    if buf.strip():
        parts.append(buf.strip())
    return parts or ([text.strip()] if text.strip() else [])


class BM25Index:
    """Keyword retrieval over chunked documents. k1=1.5, b=0.75."""

    def __init__(self) -> None:
        self.chunks: List[Dict[str, Any]] = []
        self.idf: Dict[str, float] = {}
        self.avgdl = 1.0
        self.built = False

    def add_doc(self, title: str, text: str, kind: str = "local",
                url: str = "", doc_id: str = "") -> int:
        added = 0
        for piece in chunk_text(text):
            toks = tokens(piece)
            if len(toks) < 4:
                continue
            self.chunks.append({
                "title": title, "text": piece, "kind": kind, "url": url,
                "doc_id": doc_id or slug(title), "tokens": toks, "tf": Counter(toks),
            })
            added += 1
        return added

    def build(self) -> None:
        n = max(len(self.chunks), 1)
        df: Counter = Counter()
        for c in self.chunks:
            for w in set(c["tokens"]):
                df[w] += 1
        self.idf = {w: math.log(1 + (n - d + 0.5) / (d + 0.5)) for w, d in df.items()}
        self.avgdl = sum(len(c["tokens"]) for c in self.chunks) / n
        self.built = True

    def search(self, query: str, k: int = 8) -> List[Dict[str, Any]]:
        if not self.chunks:
            return []
        q = tokens(query)
        if not q:
            q = tokens(search_terms(query))
        scores: List[Tuple[float, int]] = []
        for i, c in enumerate(self.chunks):
            dl = len(c["tokens"])
            score = 0.0
            for w in set(q):
                tf = c["tf"].get(w, 0)
                if not tf:
                    continue
                idf = self.idf.get(w, 0.0)
                score += idf * (tf * 2.5) / (tf + 1.5 * (0.25 + 0.75 * dl / self.avgdl))
            if score > 0:
                scores.append((score, i))
        scores.sort(reverse=True)
        return [dict(self.chunks[i], score=round(s, 3)) for s, i in scores[:k]]


INDEX = BM25Index()
INDEX_LOCK = threading.RLock()


def rebuild_index() -> int:
    """Load curated KB + every cached Wikipedia article into the index."""
    with INDEX_LOCK:
        INDEX.chunks.clear()
        for topic in KB:
            # Headings are intentionally left out of the chunk text: a bare
            # "How it works." would otherwise become a bogus short sentence.
            body = topic.get("summary", "") + "\n\n"
            for sec in topic.get("sections", []):
                body += sec.get("text", "") + "\n\n"
            body += topic.get("example", "") + "\n\n" + topic.get("code", "")
            INDEX.add_doc(topic["title"], body, kind="curated", doc_id=topic["id"])
        learned = 0
        for path in sorted(LEARNED_DIR.glob("*.json")):
            try:
                art = json.loads(path.read_text(encoding="utf-8"))
                INDEX.add_doc(art["title"], art.get("extract", ""), kind="wikipedia",
                              url=art.get("url", ""), doc_id=slug(art["title"]))
                learned += 1
            except Exception:
                continue
        INDEX.build()
        return learned


LEARNED_AT_STARTUP = rebuild_index()


def topic_lookup(text: str) -> Optional[Dict[str, Any]]:
    low = " " + re.sub(r"[^a-z0-9+#. ]", " ", text.lower()) + " "
    best = None
    for topic in KB:
        for alias in [topic["id"]] + topic.get("aliases", []):
            if re.search(r"(?<![a-z])" + re.escape(alias.lower()) + r"(?![a-z])", low):
                if best is None or len(alias) > len(best[0]):
                    best = (alias, topic)
    return best[1] if best else None


# ---------------------------------------------------------------------------
# Wikipedia research + local cache ("learning")
# ---------------------------------------------------------------------------


_WIKI_LOCK = threading.Lock()
_WIKI_LAST_CALL = [0.0]
_WIKI_MIN_INTERVAL = 0.35  # be polite to Wikipedia's API
WIKI_SEARCH_CACHE: Dict[str, Tuple[float, List[Dict[str, str]]]] = {}
_WIKI_COOLDOWN = [0.0]  # circuit breaker after a 429, so we fail fast instead of stalling


def clean_wiki(text: str) -> str:
    """Repair extracts: drop headings/reference debris and rejoin wrapped lines."""
    return q.clean_wiki(text)


def wiki_get(params: Dict[str, Any], timeout: float = 8.0,
            simple: bool = False) -> Dict[str, Any]:
    base = "https://simple.wikipedia.org/w/api.php" if simple else WIKI_API
    url = base + "?" + urlencode(params)
    req = urlrequest.Request(url, headers={"User-Agent": USER_AGENT, "Accept": "application/json"})
    if time.time() < _WIKI_COOLDOWN[0]:
        raise RuntimeError("Wikipedia temporarily rate-limited - using cached/local knowledge")
    for attempt in range(2):
        with _WIKI_LOCK:
            gap = time.time() - _WIKI_LAST_CALL[0]
            if gap < _WIKI_MIN_INTERVAL:
                time.sleep(_WIKI_MIN_INTERVAL - gap)
            _WIKI_LAST_CALL[0] = time.time()
        try:
            with urlrequest.urlopen(req, timeout=timeout) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except HTTPError as exc:
            if exc.code == 429:
                _WIKI_COOLDOWN[0] = time.time() + 45
                if attempt == 0:
                    time.sleep(0.8)
                    continue
                raise RuntimeError("Wikipedia rate limit (429)")
            raise
    raise RuntimeError("Wikipedia request failed")


def cache_article(title: str, extract: str, url: str,
                  name: Optional[str] = None) -> None:
    LEARNED_DIR.mkdir(parents=True, exist_ok=True)
    path = LEARNED_DIR / (name or (slug(title) + ".json"))
    path.write_text(json.dumps({
        "title": title, "url": url, "extract": extract[:70000], "fetched_at": time.time()
    }, ensure_ascii=False), encoding="utf-8")
    files = sorted(LEARNED_DIR.glob("*.json"), key=lambda p: p.stat().st_mtime)
    while len(files) > MAX_LEARNED:
        try:
            files.pop(0).unlink()
        except OSError:
            break


def cached_count() -> int:
    return len(list(LEARNED_DIR.glob("*.json")))


def wikipedia_search(query: str, limit: int = 4,
                     simple: bool = False) -> List[Dict[str, str]]:
    key = f"{query[:120]}|{limit}|{'simple' if simple else 'en'}"
    hit = WIKI_SEARCH_CACHE.get(key)
    if hit and time.time() - hit[0] < 600:
        return hit[1]
    data = wiki_get({"action": "query", "list": "search", "srsearch": query,
                     "srlimit": limit, "format": "json", "formatversion": 2},
                    simple=simple)
    out = []
    for r in data.get("query", {}).get("search", []):
        out.append({"title": r.get("title", ""),
                    "snippet": strip_html(r.get("snippet", "")),
                    "url": wiki_url(r.get("title", ""), simple)})
    WIKI_SEARCH_CACHE[key] = (time.time(), out)
    return out


def cached_article(title: str, simple: bool = False) -> Optional[Dict[str, Any]]:
    name = slug(title) + ("__simple" if simple else "") + ".json"
    path = LEARNED_DIR / name
    if not path.exists():
        return None
    try:
        art = json.loads(path.read_text(encoding="utf-8"))
        if time.time() - art.get("fetched_at", 0) > 7 * 86400:
            return None
        return art
    except Exception:
        return None


def wikipedia_read(title: str, chars: int = 14000, simple: bool = False,
                   cache: bool = True) -> Optional[Dict[str, Any]]:
    cached = cached_article(title, simple) if cache else None
    if cached and len(cached.get("extract", "")) > 200:
        full = cached["extract"]
        return {"title": cached["title"], "url": cached["url"],
                "extract": full[:chars], "lead": full[:1600], "chars": len(full)}
    data = wiki_get({"action": "query", "prop": "extracts", "explaintext": 1,
                     "titles": title, "redirects": 1, "format": "json", "formatversion": 2},
                    simple=simple)
    pages = data.get("query", {}).get("pages", [])
    if not pages or pages[0].get("missing"):
        return None
    page = pages[0]
    full = clean_wiki(page.get("extract", "") or "")
    if len(full) < 80:
        return None
    real_title = page.get("title", title)
    url = wiki_url(real_title, simple)
    if cache:
        name = slug(real_title) + ("__simple" if simple else "") + ".json"
        cache_article(real_title, full, url, name=name)
    return {"title": real_title, "url": url, "extract": full[:chars],
            "lead": full[:1600], "chars": len(full)}


def learn_topic(topic: str, ctx: "Context") -> str:
    ctx.step("Teaching Ryzek a topic", topic[:90])
    if not ONLINE or not ctx.online:
        return ("## Learning is offline\n\nLive research is disabled (`RYZEK_ONLINE=0`). "
                "You can still add unlimited information by editing `knowledge_base.json` - "
                "every `sections[].text` is indexed automatically on restart.")
    try:
        results = wikipedia_search(topic, 2)
    except Exception as exc:
        return f"## Could not reach Wikipedia\n\n{type(exc).__name__}: {exc}\n\nAdd the topic to `knowledge_base.json` instead and restart - no network needed."
    if not results:
        return (f"## No article found for \"{topic}\"\n\nTry a broader noun phrase, or add it to "
                "`knowledge_base.json`. The curated base currently has {len(KB)} topics.")
    art = wikipedia_read(results[0]["title"], chars=60000)
    if not art:
        return f"## \"{results[0]['title']}\" returned no readable text\n\nTry a different title."
    count = rebuild_index()
    ctx.sources.append({"title": art["title"], "url": art["url"], "kind": "wikipedia",
                        "excerpt": condense(art["extract"], 1)[:220]})
    return (
        f"## Learned: {art['title']}\n\n{condense(art['extract'], 5, 1100)}\n\n"
        f"## What changed\n\n- Cached {art['chars']:,} characters of article text in `data/learned/`.\n"
        f"- Rebuilt the retrieval index: {len(INDEX.chunks)} chunks from {len(KB)} curated topics and {count} cached articles.\n"
        f"- Future questions about this subject can now be answered from the local cache even with no internet.\n\n"
        f"Source: [{art['title']}]({art['url']})"
    )


# ---------------------------------------------------------------------------
# Tool registry (plugin system)
# ---------------------------------------------------------------------------

TOOL_REGISTRY: Dict[str, Dict[str, Any]] = {}


def tool(name: str, description: str, schema: Dict[str, Any]):
    def decorator(fn):
        TOOL_REGISTRY[name] = {"fn": fn, "description": description, "schema": schema}
        return fn
    return decorator


def tool_specs() -> List[Dict[str, Any]]:
    return [{"type": "function", "function": {
        "name": n, "description": t["description"], "parameters": t["schema"]
    }} for n, t in TOOL_REGISTRY.items()]


@dataclass
class Context:
    session: "Session"
    depth: str = "deep"
    online: bool = True
    emit: Optional[Callable[[Dict[str, Any]], None]] = None
    steps: List[Dict[str, str]] = field(default_factory=list)
    sources: List[Dict[str, str]] = field(default_factory=list)
    note: str = ""
    opts: Dict[str, Any] = field(default_factory=dict)
    web_items: List[Dict[str, str]] = field(default_factory=list)
    web_status: List[Dict[str, Any]] = field(default_factory=list)
    # --- v2.6: who is asking, what Ryzek understood, what it remembers
    user: Optional[Dict[str, Any]] = None
    understanding: Optional[Any] = None
    memory: Optional[Any] = None
    recalled: List[Dict[str, Any]] = field(default_factory=list)
    local_hits: List[Dict[str, Any]] = field(default_factory=list)
    everyday: str = ""
    priority_sources: List[str] = field(default_factory=list)

    @property
    def user_id(self) -> Optional[int]:
        return (self.user or {}).get("id")

    def step(self, label: str, detail: str = "") -> None:
        self.steps.append({"label": label, "detail": detail[:180]})
        if self.emit:
            try:
                self.emit({"type": "step", "label": label, "detail": detail[:180]})
            except Exception:
                pass


def run_tool(name: str, args: Dict[str, Any], ctx: Context) -> str:
    entry = TOOL_REGISTRY.get(name)
    if not entry:
        return f"Unknown tool '{name}'. Available: {', '.join(TOOL_REGISTRY)}"
    preview = ", ".join(f"{k}={str(v)[:40]}" for k, v in (args or {}).items())
    ctx.step(f"Tool: {name}", preview)
    try:
        return str(entry["fn"](args or {}, ctx))
    except Exception as exc:
        return f"Tool '{name}' failed: {type(exc).__name__}: {exc}. Answer using your own reasoning."


_OBJ = {"type": "object", "properties": {}, "required": []}


def _schema(props: Dict[str, Any], required: List[str]) -> Dict[str, Any]:
    return {"type": "object", "properties": props, "required": required}


_S = lambda t, d="": {"type": t, "description": d}  # noqa: E731


@tool("calculator", "Safely evaluate arithmetic. Accepts natural language like '17% of 240' or 'sqrt(81) + 2^10'. Always use instead of mental maths.",
      _schema({"expression": _S("string", "The arithmetic expression")}, ["expression"]))
def t_calculator(a, ctx):
    return calculator(a.get("expression", ""))


@tool("detailed_math", "Show a full worked solution with steps for an arithmetic expression.",
      _schema({"expression": _S("string")}, ["expression"]))
def t_detailed_math(a, ctx):
    return detailed_math(a.get("expression", ""))


@tool("current_time", "Get the current local date and time.",
      _schema({"timezone": _S("string", "IANA zone e.g. Asia/Karachi")}, []))
def t_time(a, ctx):
    return current_time(a.get("timezone", ""))


@tool("convert_unit", "Convert length, mass, volume or temperature units.",
      _schema({"value": _S("number"), "from_unit": _S("string"), "to_unit": _S("string")},
              ["value", "from_unit", "to_unit"]))
def t_convert(a, ctx):
    return convert_unit(a.get("value", 0), a.get("from_unit", ""), a.get("to_unit", ""))


@tool("flip_coin", "Flip a fair coin.", _OBJ)
def t_coin(a, ctx):
    return "Coin flip: " + random.choice(["Heads", "Tails"])


@tool("roll_dice", "Roll dice, e.g. 3 d20.",
      _schema({"sides": _S("integer"), "count": _S("integer")}, []))
def t_dice(a, ctx):
    sides = max(2, min(int(a.get("sides", 6)), 1000))
    count = max(1, min(int(a.get("count", 1)), 20))
    rolls = [random.randint(1, sides) for _ in range(count)]
    return f"Rolled {count}d{sides}: {', '.join(map(str, rolls))} (total {sum(rolls)})"


@tool("pick_one", "Randomly choose between comma/or-separated options.",
      _schema({"options": _S("string")}, ["options"]))
def t_pick(a, ctx):
    parts = [p.strip() for p in re.split(r"\s*(?:,|\bor\b|\bvs\.?\b|\|)\s*", a.get("options", "")) if p.strip()]
    return f"I'd pick: {random.choice(parts)}" if parts else "Give me two or more options."


@tool("remember", "Save a fact about the user into persistent chat memory.",
      _schema({"key": _S("string"), "value": _S("string")}, ["key", "value"]))
def t_remember(a, ctx):
    k = str(a.get("key", "note")).strip()[:60] or "note"
    ctx.session.facts[k] = str(a.get("value", "")).strip()[:300]
    return f"Remembered '{k}' = '{ctx.session.facts[k]}'."


@tool("recall", "Read saved facts. Empty key lists everything.",
      _schema({"key": _S("string")}, []))
def t_recall(a, ctx):
    facts = ctx.session.facts
    if not facts:
        return "No facts saved in this chat yet."
    key = str(a.get("key", "")).lower()
    hits = {k: v for k, v in facts.items() if not key or key in k.lower() or key in v.lower()}
    return "; ".join(f"{k}: {v}" for k, v in hits.items()) if hits else f"No match for '{key}'. Keys: {', '.join(facts)}"


@tool("local_search", "Search Ryzek's curated knowledge base and cached Wikipedia articles with BM25. Returns the most relevant passages.",
      _schema({"query": _S("string"), "k": _S("integer")}, ["query"]))
def t_local(a, ctx):
    with INDEX_LOCK:
        hits = INDEX.search(a.get("query", ""), int(a.get("k", 6) or 6))
    if not hits:
        return "No local passages matched. Try wikipedia_search."
    return "\n\n".join(f"[{h['title']}] {h['text'][:420]}" for h in hits)


@tool("wikipedia_search", "Search Wikipedia for authoritative articles on a topic. Returns titles, snippets and URLs. Use this first for factual questions.",
      _schema({"query": _S("string"), "limit": _S("integer")}, ["query"]))
def t_wsearch(a, ctx):
    if not ONLINE or not ctx.online:
        return "Live research is disabled. Use local_search instead."
    q = a.get("query", "")
    results = wikipedia_search(q, int(a.get("limit", 4) or 4))
    if not results:
        results = wikipedia_search(search_terms(q), int(a.get("limit", 4) or 4))
    for r in results:
        if not any(s["url"] == r["url"] for s in ctx.sources):
            ctx.sources.append({"title": r["title"], "url": r["url"],
                                "kind": "wikipedia", "excerpt": r["snippet"][:220]})
    return "\n".join(f"{i+1}. {r['title']} - {r['url']} - {r['snippet'][:160]}" for i, r in enumerate(results)) or "No results."


@tool("wikipedia_read", "Read the full plain-text extract of a Wikipedia article and cache it locally. Call this on the best titles from wikipedia_search.",
      _schema({"title": _S("string"), "chars": _S("integer")}, ["title"]))
def t_wread(a, ctx):
    if not ONLINE or not ctx.online:
        return "Live research is disabled."
    art = wikipedia_read(a.get("title", ""), int(a.get("chars", 12000) or 12000))
    if not art:
        return "Article not found or has no extract."
    with INDEX_LOCK:
        INDEX.add_doc(art["title"], art["extract"], kind="wikipedia", url=art["url"])
        INDEX.build()
    if not any(s["url"] == art["url"] for s in ctx.sources):
        ctx.sources.append({"title": art["title"], "url": art["url"],
                            "kind": "wikipedia", "excerpt": condense(art["extract"], 1)[:220]})
    return f"TITLE: {art['title']}\nURL: {art['url']}\nLENGTH: {art['chars']} chars\n\n{art['extract']}"


@tool("learn_topic", "Permanently cache a Wikipedia article into Ryzek's local knowledge so future questions work offline.",
      _schema({"topic": _S("string")}, ["topic"]))
def t_learn(a, ctx):
    return learn_topic(a.get("topic", ""), ctx)


@tool("knowledge_status", "Report how many curated topics, cached articles and indexed chunks Ryzek currently has.",
      _OBJ)
def t_kstatus(a, ctx):
    with INDEX_LOCK:
        return (f"{len(KB)} curated topics, {cached_count()} cached Wikipedia articles, "
                f"{len(INDEX.chunks)} indexed chunks, {len(TOOL_REGISTRY)} tools.")


# ---------------------------------------------------------------------------
# Detailed answer composition
# ---------------------------------------------------------------------------


def detailed_math(raw: str) -> str:
    line = calculator(raw)
    expr, value = line.rsplit(" = ", 1)
    return (
        f"## Answer\n\n**{value}**  \nParsed expression: `{expr}`\n\n"
        "## Worked steps\n\n"
        f"1. **Read the input.** Your message was normalised to `{expr}`. Word operators become symbols "
        "(`times` -> `*`, `divided by` -> `/`), `17%` becomes `17/100`, `^` becomes `**`.\n"
        "2. **Apply precedence.** Parentheses first, then powers, then multiplication/division, then addition/subtraction.\n"
        f"3. **Evaluate safely.** An allow-listed AST evaluator computes the value: **{value}**.\n"
        "4. **Check.** Re-evaluating the same expression reproduces the result.\n\n"
        "## Why this is safe\n\nThe calculator parses a restricted syntax tree; it never calls Python's `eval()`. "
        "Names, attribute access, imports and arbitrary function calls are rejected, so injected code cannot run.\n\n"
        "## Common mistakes\n\n- Forgetting that `%` means 'per hundred' - `17% of 240` is `(17/100)*240`, not `17*240`.\n"
        "- Assuming `2^10` is XOR. In maths it is exponentiation, so Ryzek converts it to `2**10`.\n"
        "- Dividing by zero, which is undefined and is reported as a clean error instead of a crash.\n\n"
        "## Try next\n\nGive me a bracketed expression, a percentage, a square root, or ask me to convert the result into another unit."
    )


def detailed_conversion(value: str, src: str, dst: str) -> str:
    line = convert_unit(value, src, dst)
    cs, cd = canonical_unit(src), canonical_unit(dst)
    if cs in ("c", "f", "k"):
        mechanism = (
            f"1. Temperature scales are **affine**, not simple ratios: they differ by both an offset and a scale.\n"
            f"2. Convert `{src}` to Celsius first: `C = (F - 32) x 5/9` for Fahrenheit, or `C = K - 273.15` for Kelvin.\n"
            f"3. Convert Celsius to `{dst}`: `F = C x 9/5 + 32`, `K = C + 273.15`.\n"
            f"4. Result: {line}.\n"
        )
    else:
        a, fa = _UNITS[cs]
        b, fb = _UNITS[cd]
        mechanism = (
            f"1. Both units are expressed in a common base ({a}: `{src}` uses factor {fa:g}, `{dst}` uses factor {fb:g}).\n"
            f"2. Convert to the base: `{value} x {fa:g}`.\n"
            f"3. Convert from the base to the target: divide by `{fb:g}`.\n"
            f"4. Result: {line}.\n"
        )
    return (
        f"## Answer\n\n**{line}**\n\n"
        "## How the conversion works\n\n" + mechanism + "\n"
        "## Sanity check\n\nConverting the result back should recover the original number; temperature uses the affine "
        "formulas `(F-32)*5/9` and `C*9/5+32` rather than a simple ratio.\n\n"
        "## Common mistakes\n\n- Mixing incompatible dimensions (length vs mass) - Ryzek rejects those.\n- Confusing `lb` (pound mass) with pound-force, or miles with nautical miles.\n- Rounding too early; keep full precision until the final step.\n\n"
        "## Try next\n\nAsk for another unit pair, or ask me to explain the underlying physical quantity in detail."
    )


def diversify(hits: List[Dict[str, Any]], depth: str) -> List[Dict[str, Any]]:
    cap = {"quick": 2, "standard": 4, "deep": 7, "exhaustive": 20}.get(depth, 7)
    per_title_max = 8 if depth == "exhaustive" else 2
    per_title: Counter = Counter()
    out = []
    for h in hits:
        if per_title[h["title"]] >= per_title_max:
            continue
        per_title[h["title"]] += 1
        out.append(h)
        if len(out) >= cap:
            break
    return out


def best_summary(question: str, hits: List[Dict[str, Any]]) -> str:
    """Pick the sentences that actually answer the question, not just chunk starts."""
    qwords = set(tokens(question))
    cands: List[Tuple[float, str]] = []
    for h in hits[:10]:
        for s in sentences(clean_wiki(h["text"])):
            if not (55 <= len(s) <= 330) or re.match(r"^=+", s):
                continue
            score = 2.0 * len(qwords & set(tokens(s)))
            if re.search(r"\b(is|are|was|were|refers to|means|defined as|known as|occurs|happens|caused by)\b", s.lower()):
                score += 2.5
            score += min(len(s) / 220, 1.0)
            cands.append((score, s))
    if not cands:
        return condense(clean_wiki(hits[0]["text"]), 2)
    cands.sort(key=lambda x: -x[0])
    chosen, seen = [], set()
    for _, s in cands:
        k = s[:55].lower()
        if k in seen:
            continue
        seen.add(k)
        chosen.append(s.rstrip(".") + ".")
        if len(chosen) >= 2:
            break
    return " ".join(chosen)[:800]


def best_lead(question: str, leads: List[str]) -> str:
    """Wikipedia article leads are the most reliable short answer available."""
    q = set(tokens(question))
    causal_q = bool(re.match(r"^\s*why\b", question.lower()))
    best_text, best_score = "", -1.0
    for i, lead in enumerate(leads):
        sents = [s for s in sentences(clean_wiki(lead)) if 25 <= len(s) <= 340]
        if not sents:
            continue
        score = 3.0 * len(q & set(tokens(sents[0])))
        score += sum(len(q & set(tokens(s))) for s in sents[1:4])
        score += 5.0 * (len(leads) - i)  # strongly prefer Wikipedia's top-ranked source
        if re.search(r"\b(is|are|refers to|caused by|due to|occurs|describes)\b", sents[0].lower()):
            score += 2.0
        if causal_q and re.search(r"scatter|because|due to|caused by|wavelength|absorb|reflect|radiation", lead.lower()):
            score += 5.0
        if score > best_score:
            best_score, best_text = score, " ".join(sents[:2])
    return best_text[:800]


def key_points(question: str, hits: List[Dict[str, Any]], n: int = 5) -> List[str]:
    qwords = set(tokens(question))
    candidates: List[Tuple[int, str]] = []
    for h in hits:
        for s in sentences(clean_wiki(h["text"])):
            if len(s) < 45 or len(s) > 260 or re.match(r"^=+", s):
                continue
            overlap = len(qwords & set(tokens(s)))
            candidates.append((overlap + min(len(s) // 120, 1), s))
    candidates.sort(key=lambda x: -x[0])
    out, seen = [], set()
    for _, s in candidates:
        key = s[:60].lower()
        if key in seen:
            continue
        seen.add(key)
        out.append(s.rstrip(".") + ".")
        if len(out) >= n:
            break
    return out or ["The sources agree on the core definition but differ in scope and emphasis."]


def practical_angle(question: str, hits: List[Dict[str, Any]]) -> str:
    first = hits[0]["text"] if hits else ""
    lead = condense(first, 1, 240)
    return (
        f"To make \"{' '.join(question.split())[:110]}\" concrete, start from the definition above "
        f"and change one variable at a time. {lead}\n\n"
        "A reliable pattern: (1) name the thing precisely, (2) identify the mechanism or rule, "
        "(3) plug in a small example you can check by hand, (4) compare with a second source, "
        "(5) note where the rule stops applying. If you tell me your actual goal - an exam answer, "
        "a project decision, or code - I'll rewrite this section around it."
    )


def long_scaffold(question: str, ctx: Context) -> str:
    q = " ".join(question.split())[:180]
    low = q.lower()
    if low.startswith(("why", "how come")):
        principle = "Causes usually sit at one of three levels: mechanism (what physically happens), incentive (what the actors gain), or constraint (what limits the options). Naming the level turns most 'why' questions into answerable ones."
    elif low.startswith(("how", "can you", "can i")):
        principle = "A 'how' is a sequence of verifiable steps. Find the smallest action whose result you can observe, take it, then repeat with what you learned."
    elif low.startswith(("who", "when", "where")):
        principle = "For a specific person, date or place, the trustworthy route is a primary source: an official record, a timestamped document, or the organisation's own page."
    else:
        principle = "Every well-posed question has three parts: the subject, the property being asked about, and the context that fixes its meaning. Pin those down and the answer space collapses fast."

    with INDEX_LOCK:
        related = list(dict.fromkeys(c["title"] for c in INDEX.chunks))[:8]
    related_md = "\n".join(f"- {t}" for t in related) or "- (load knowledge_base.json to populate this)"

    return (
        f"## Short answer\n\nI couldn't verify the specific facts behind \"{q}\" from the sources loaded right now, "
        "so I'm not going to invent them. Here is the complete, useful answer I *can* give: the question is "
        "answerable, and the fastest route is to fix the interpretation, then check one authoritative source. "
        "Everything you need to do that is below.\n\n"
        "## What this question is really asking\n\n"
        f"- **Subject:** the entity or concept in \"{q[:80]}\".\n"
        "- **Property:** the attribute being asked about (cause, definition, value, comparison, procedure).\n"
        "- **Context:** the time, place, assumptions and audience that make one answer correct instead of another.\n"
        f"- **General principle:** {principle}\n\n"
        "## How to work it out, step by step\n\n"
        "1. Restate the question in one sentence with no ambiguous words.\n"
        "2. List what is already known and what is actually unknown.\n"
        "3. Choose an authoritative source type (primary record, official documentation, peer-reviewed work, or a reputable encyclopaedia).\n"
        "4. Extract the claim, the date and the source, then cross-check against a second independent source.\n"
        "5. Apply any rule or formula explicitly, showing the intermediate values.\n"
        "6. State the answer with its uncertainty and the conditions under which it would change.\n\n"
        "## Worked example\n\n"
        "Suppose the question were \"how much is 17% of 240?\". Restate it as `0.17 x 240`, compute `40.8`, "
        "then check by dividing `40.8 / 240 = 0.17`. That same six-step pattern works for factual questions - "
        "replace the arithmetic with evidence extraction and citation.\n\n"
        "## Common mistakes and limits\n\n"
        "- Accepting the first confident-sounding answer without a source.\n"
        "- Mixing a definition question with a value question (they need different evidence).\n"
        "- Assuming a model's training data includes today's events. It does not.\n"
        "- Ignoring units, time zones, or the version of a product/standard being discussed.\n\n"
        "## Where to get the exact answer\n\n"
        "- **Ask me again with more context** (a date, a field, a specific entity) - I research Wikipedia live and cache it.\n"
        f"- **Teach me the topic:** type `/learn {' '.join(search_terms(q).split()[:3]) or 'your topic'}` and I will fetch and permanently cache the article.\n"
        "- **Turn on the LLM brain:** set `RYZEK_API_KEY` (see README) so I can reason across sources in one pass.\n"
        "- **Add it yourself:** drop a new entry into `knowledge_base.json`; it is indexed on restart.\n\n"
        "## Related things I do know in detail\n\n" + related_md + "\n\n"
        "## Sources\n\n- Curated knowledge base (`knowledge_base.json`), "
        f"{len(KB)} topics / " + str(len(INDEX.chunks)) + " indexed chunks.\n"
        "- No external page matched this query, so no external source is being claimed.\n\n"
        "## What I could not verify\n\n"
        "The specific factual payload of your question. I am telling you that explicitly rather than "
        "fabricating a citation.\n\n"
        "## Keep going\n\n"
        "One question that would sharpen this immediately: what is the concrete thing you need to decide or "
        "write down? Give me that and I'll turn this framework into a direct, sourced answer."
    )


def collect_material(hits: List[Dict[str, Any]], ctx: Context,
                     question: str = "") -> List[Tuple[str, str]]:
    """v2.6: turn retrieved passages into (sentence, source title) pairs."""
    out: List[Tuple[str, str]] = []
    seen = set()
    for h in hits:
        title = h.get("title", "")
        for sent in answer_kit.sentences(h.get("text", "")):
            key = sent[:90].lower()
            if key in seen:
                continue
            seen.add(key)
            out.append((sent, title))
    # the curated topic's own summary sentences go first (highest trust)
    t = topic_lookup(question) if question else None
    if t:
        body = t.get("summary", "")
        for sent in answer_kit.sentences(q.clean_wiki(body)):
            key = sent[:90].lower()
            if key in seen:
                continue
            seen.add(key)
            out.insert(0, (sent, t["title"]))
    return out


def filter_material(material: List[Tuple[str, str]], u: Any,
                    strict: bool = False) -> List[Tuple[str, str]]:
    """Keep only sentences that are really about the understood subject.

    Two levels of checking, because sentence-level keyword matching let
    unrelated articles through (a black-hole page mentioning "affect", an
    article about a TV character mentioning "phone"):

      1. the SOURCE must be about the subject (its title or repeated terms)
      2. the SENTENCE must mention the subject phrase or two of its words
    """
    subject = getattr(u, "subject", "") or ""
    if not subject:
        return material

    subj_terms = set(understand.content_terms(subject))
    # multi-word phrases are much stronger evidence than single words
    phrases = []
    for part in re.split(r"\s+vs\s+|\s+and\s+", subject):
        words = [w for w in re.findall(r"[a-z0-9]+", part.lower()) if len(w) > 3]
        if len(words) >= 2:
            phrases.append(" ".join(words[:2]))
            phrases.append(" ".join(words))
    strong_words = {w for w in subj_terms if len(w) >= 5}

    def source_ok(title: str) -> bool:
        t = set(understand.content_terms(title or ""))
        return bool(t & subj_terms) or any(p in (title or "").lower() for p in phrases)

    by_source: Dict[str, List[Tuple[str, str]]] = {}
    for sent, src in material:
        by_source.setdefault(src, []).append((sent, src))

    keep: List[Tuple[str, str]] = []
    for src, rows in by_source.items():
        good_source = source_ok(src)
        hits = []
        for sent, _ in rows:
            low = sent.lower()
            phrase_hit = any(p in low for p in phrases)
            word_hits = sum(1 for w in strong_words if w in low)
            if phrase_hit or word_hits >= 2 or (good_source and word_hits >= 1):
                hits.append((sent, src))
        keep.extend(hits)

    # Nothing survived: report no material so the caller can be honest rather
    # than quoting sentences from the wrong article.
    if strict:
        return keep
    return keep


POETS_TITLE = {k: v['title'] for k, v in poetry_kit.POETS.items()}


def synthesize(question: str, ctx: Context) -> Optional[str]:
    """v2.6: write an answer from understood material.

    Returns None when there is not enough trustworthy material, so the caller
    can show an honest 'give me one detail' reply instead of boilerplate.
    """
    u = ctx.understanding or understand.analyze(question, ctx.session)
    ctx.understanding = u
    search_for = retrieval_query(question, ctx)

    # 1) curated everyday knowledge first: it is checked and plainly written
    entry = everyday.find(getattr(u, "subject", "") or "", question)
    material: List[Tuple[str, str]] = []
    if entry:
        ctx.everyday = entry["title"]
        ctx.step("Using checked everyday knowledge", entry["title"])
        material.extend((line, entry["title"]) for line in everyday.material(entry))

    # 2) local retrieval
    material += collect_material(ctx.local_hits, ctx, search_for)
    with INDEX_LOCK:
        wider = INDEX.search(search_for, k=20 if ctx.depth == "exhaustive" else 12)
    material += collect_material(wider, ctx, search_for)
    # v2.6: keep only sentences about the understood subject. Without this,
    # "affect vs effect" kept black-hole and fuel-sulfur sentences that merely
    # contain the word "effect".
    if entry:
        curated = [(line, entry["title"]) for line in everyday.material(entry)]
        others = [(sent, src) for sent, src in material if src != entry["title"]]
        # A rich curated entry is the answer. Extra material may join only if
        # it clearly mentions the subject AND the curated text is thin - this
        # is what stopped a Wikipedia LED sentence sneaking into a battery
        # answer.
        extra = filter_material(others, u, strict=True) if len(curated) < 8 else []
        material = curated + extra
        ctx.sources.insert(0, {"title": entry["title"], "url": "",
                               "kind": "checked Ryzek library", "excerpt": entry["what"][:180]})
        ctx.priority_sources = [entry["title"]]
    else:
        material = filter_material(material, u)
    if ctx.web_items:
        for it in ctx.web_items:
            for sent in answer_kit.sentences(it.get("text") or it.get("snippet") or ""):
                material.append((sent, it.get("title", "")))

    sources = list(ctx.sources)
    pri = ctx.priority_sources

    if u.intent in ("howto",) and len(material) >= 6:
        b = answer_kit.build_step_guide(u, material, sources, pri)
    elif u.is_wide or u.intent == "wide":
        b = answer_kit.build_wide(u, material, sources, ctx.depth, pri)
    else:
        b = answer_kit.build_general(u, material, sources, ctx.depth, pri)

    if not b.confident or len(b.sections) == 0:
        return None
    ctx.step("Writing the answer", f"{u.intent} shape · {len(material)} candidate facts")
    return b.render()


def pin_topic(question: str, hits: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Put the exact curated topic first, so 'what is a ghazal?' opens with the
    ghazal definition rather than a loosely related poet's biography."""
    topic = topic_lookup(question)
    if not topic:
        return hits
    title = topic["title"]
    front = [h for h in hits if h.get("title") == title]
    rest = [h for h in hits if h.get("title") != title]
    return front + rest


def focus_hits(question: str, hits: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Drop loosely related passages so long answers stay on the exact subject."""
    qt = set(tokens(question))
    if not hits or not qt:
        return hits
    scored = []
    for h in hits:
        title_terms = set(tokens(h.get("title", "")))
        text_terms = set(tokens(h.get("text", "")[:500]))
        scored.append((4 * len(qt & title_terms) + len(qt & text_terms), h))
    top = max(s for s, _ in scored)
    floor = max(1.0, top * 0.25)
    kept = [h for s, h in scored if s >= floor]
    if len(kept) < 6:                       # keep enough breadth for long answers
        kept = [h for _, h in scored[:8]]
    return kept[:24] or [hits[0]]


def compose_answer(question: str, hits: List[Dict[str, Any]], ctx: Context,
                   leads: Optional[List[str]] = None) -> str:
    """Delegate to the v2.1 quality composer: exhaustive, deduplicated headings."""
    picked = diversify(hits, ctx.depth)
    if not picked:
        return long_scaffold(question, ctx)
    o = q.default_opts(ctx.opts)
    if o["simple_english"]:
        o["style"] = "simple"
    topic = topic_lookup(question)
    terms = ([(sec.get("heading", "Concept"), sec.get("text", ""))
              for sec in topic.get("sections", [])] if topic else None)
    return q.compose_answer(
        question=question, hits=picked, leads=leads or [], sources=ctx.sources,
        depth=ctx.depth, opts=o, kb_count=len(KB),
        chunks=len(KB) * 2 + cached_count(), terms=terms,
    )


def retrieval_query(question: str, ctx: Context) -> str:
    """v2.6: search with the understood SUBJECT, not the raw sentence.

    "what is the difference between affect and effect" used to retrieve passages
    about the greenhouse effect because 'effect' dominated the keyword score.
    The understanding layer pulls out "affect vs effect", which is specific
    enough to retrieve the right passages.
    """
    u = ctx.understanding
    if u is not None and getattr(u, "subject", ""):
        terms = " ".join(getattr(u, "subject_terms", [])[:8])
        return terms or u.subject
    return question


def research(question: str, ctx: Context) -> str:
    o = q.default_opts(ctx.opts)
    ctx.step("Understanding the question",
             (ctx.understanding.intent + (" · " + ctx.understanding.subject
              if getattr(ctx.understanding, "subject", "") else ""))
             if ctx.understanding is not None else f"depth: {ctx.depth}")
    search_for = retrieval_query(question, ctx)
    with INDEX_LOCK:
        local_hits = INDEX.search(search_for, k=10)
    ctx.local_hits = local_hits
    ctx.step("Searching curated knowledge", f"{len(local_hits)} passage matches")

    # v2.5: index the live passages so the composer actually uses them.
    if ctx.web_items:
        existing = {c.get("doc_id") for c in INDEX.chunks}
        added = 0
        with INDEX_LOCK:
            for it in ctx.web_items[:8]:
                body = it.get("text") or it.get("snippet") or ""
                if len(body) < 160:
                    continue
                did = "web-" + re.sub(r"[^a-z0-9]+", "-", it["url"].lower())[:70]
                if did in existing:
                    continue
                existing.add(did)
                INDEX.add_doc(it["title"], body, kind="web", url=it["url"], doc_id=did)
                added += 1
            if added:
                INDEX.build()
        ctx.step("Adding live web passages", f"{added} pages indexed for this answer")

    simple = bool(o["simple_english"])
    cache = bool(o["auto_learn"])
    breadth = max(1, min(4, o["breadth"]))
    if ctx.depth == "exhaustive":
        breadth = max(breadth, 2)

    leads: List[str] = []
    if ctx.online and ONLINE:
        query = build_search_query(search_for if search_for != question else question)
        ctx.step("Searching Wikipedia", query[:90])
        try:
            results = wikipedia_search(query, 5, simple=simple)
            if not results:
                results = wikipedia_search(re.sub(r"\s+", " ", question)[:120], 4, simple=simple)
            results = rank_results(question, results)[:breadth]
        except Exception as exc:
            results = []
            ctx.step("Wikipedia unavailable", f"{type(exc).__name__}: {str(exc)[:80]}")
            ctx.note = "Live research unavailable (rate-limited) - answered from cached/local knowledge."
        if results:
            first_chars = 0
            for i, r in enumerate(results):
                # One full article is usually enough; extra hits become
                # "further reading" chips instead of more network requests.
                if i == 1 and first_chars >= 4000 and ctx.depth != "exhaustive":
                    ctx.sources.append({"title": r["title"], "url": r["url"],
                                        "kind": "further reading", "excerpt": r["snippet"][:220]})
                    continue
                ctx.step("Reading source", r["title"])
                try:
                    art = wikipedia_read(r["title"], chars=16000, simple=simple, cache=cache)
                except Exception:
                    art = None
                    ctx.note = "Live research unavailable (rate-limited) - answered from cached/local knowledge."
                if art and art["extract"]:
                    if i == 0:
                        first_chars = len(art["extract"])
                    leads.append(art.get("lead", ""))
                    with INDEX_LOCK:
                        INDEX.add_doc(art["title"], art["extract"], kind="wikipedia", url=art["url"])
                        INDEX.build()
                    if not any(s["url"] == art["url"] for s in ctx.sources):
                        ctx.sources.append({"title": art["title"], "url": art["url"],
                                            "kind": "wikipedia", "excerpt": condense(art["extract"], 1)[:220]})
    with INDEX_LOCK:
        all_hits = INDEX.search(search_for, k=24 if ctx.depth == "exhaustive" else 14)
    if ctx.depth == "exhaustive":
        all_hits = focus_hits(search_for, all_hits)
    all_hits = pin_topic(question, all_hits)

    # Exhaustive answers should cover the WHOLE curated topic, not just the two
    # chunks BM25 happens to rank first. Rebuild the topic's sections as
    # passages and put them at the front; other sources remain for breadth.
    pinned_topic = topic_lookup(question)
    if pinned_topic:
        title = pinned_topic["title"]
        body = pinned_topic.get("summary", "") + "\n\n" + "\n\n".join(
            sec.get("text", "") for sec in pinned_topic.get("sections", []))
        extra = [{"title": title, "text": piece, "kind": "curated", "url": "",
                  "score": 999.0}
                 for piece in chunk_text(body, size=720)]
        # Exact curated knowledge always outranks a cached Wikipedia article
        # at EVERY depth - quick and standard included. This is what keeps a
        # short answer on topic when a random cached page wins BM25.
        limit = {"quick": 2, "standard": 4}.get(ctx.depth, len(extra))
        all_hits = extra[:limit] + [h for h in all_hits if h.get("title") != title]
    # If an exact curated topic exists and no live article was read, use its
    # summary as the opening lead so the short answer is on subject.
    if pinned_topic:
        curated_lead = pinned_topic.get("summary", "")
        if curated_lead:
            # An exact curated topic owns the short answer. Wikipedia leads are
            # still used for the detailed sections, but a loosely matched
            # article (e.g. a book review standing in for a history) must never
            # become the opening sentence.
            leads = [curated_lead]
    if not ctx.sources:
        seen_titles = set()
        for h in all_hits[:6]:
            if h["title"] in seen_titles:
                continue
            seen_titles.add(h["title"])
            ctx.sources.append({"title": h["title"], "url": h.get("url", ""),
                                "kind": "cached article" if h["kind"] == "wikipedia" else "curated",
                                "excerpt": condense(h["text"], 1)[:220]})
    q_terms = set(tokens(question))
    top_coverage = (len(q_terms & set(tokens(all_hits[0]["text"]))) / max(len(q_terms), 1)) if all_hits else 0.0
    if top_coverage < 0.34 and not leads:
        ctx.step("Low confidence match", "using the honest detailed framework")
        return long_scaffold(question, ctx)
    ctx.step("Ranking passages", f"{len(all_hits)} candidates from {len(KB)} curated topics + {cached_count()} cached articles")
    ctx.step("Writing a detailed answer")
    answer = compose_answer(question, all_hits, ctx, leads)
    if ctx.web_items:
        links = web.source_lines(ctx.web_items, n=6)
        if links:
            answer += ("\n\n## Live web sources\n\n"
                       "I checked these pages while writing this answer. Open them to verify any "
                       "figure or date yourself.\n\n" + links + "\n")
    return answer


# ---------------------------------------------------------------------------
# Optional LLM agent
# ---------------------------------------------------------------------------


class LLMAgent:
    def __init__(self) -> None:
        self.api_key = os.environ.get("RYZEK_API_KEY") or os.environ.get("OPENAI_API_KEY") or ""
        base = (os.environ.get("RYZEK_BASE_URL") or "https://api.openai.com/v1").rstrip("/")
        if base.endswith("/chat/completions"):
            base = base[: -len("/chat/completions")].rstrip("/")
        self.base_url = base
        self.model = os.environ.get("RYZEK_MODEL") or "gpt-4o-mini"
        self.use_tools = os.environ.get("RYZEK_TOOLS", "1") not in ("0", "false", "no")
        self.timeout = float(os.environ.get("RYZEK_TIMEOUT", "45"))

    @property
    def enabled(self) -> bool:
        return bool(self.api_key)

    def _post(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        req = urlrequest.Request(
            self.base_url + "/chat/completions",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json",
                     "Authorization": f"Bearer {self.api_key}",
                     "User-Agent": USER_AGENT},
            method="POST",
        )
        with urlrequest.urlopen(req, timeout=self.timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))

    def respond(self, text: str, ctx: Context) -> str:
        system = build_system_prompt(ctx.opts, ctx.depth)
        messages: List[Dict[str, Any]] = [{"role": "system", "content": system}]
        for m in ctx.session.messages[-10:]:
            if m.get("role") in ("user", "assistant") and m.get("content"):
                messages.append({"role": m["role"], "content": m["content"][:4000]})
        messages.append({"role": "user", "content": text})
        allow_tools = self.use_tools

        for _ in range(MAX_STEPS):
            payload: Dict[str, Any] = {"model": self.model, "messages": messages,
                                       "temperature": 0.5,
                                       "max_tokens": {"quick": 900, "standard": 1800,
                                                      "deep": 2800, "exhaustive": 4200}.get(ctx.depth, 2800)}
            if allow_tools:
                payload["tools"] = tool_specs()
                payload["tool_choice"] = "auto"
            try:
                data = self._post(payload)
            except HTTPError as exc:
                detail = exc.read().decode("utf-8", "replace")[:250]
                if exc.code in (400, 404, 422) and allow_tools:
                    allow_tools = False
                    ctx.step("Provider lacks tool support", "retrying without tools")
                    continue
                raise RuntimeError(f"HTTP {exc.code}: {detail}") from exc
            except (URLError, TimeoutError, OSError) as exc:
                raise RuntimeError(f"network error: {exc}") from exc

            choices = data.get("choices") or []
            if not choices:
                raise RuntimeError("API returned no choices")
            msg = choices[0].get("message") or {}
            calls = msg.get("tool_calls") or []
            if calls:
                messages.append({"role": "assistant", "content": msg.get("content") or "", "tool_calls": calls})
                for call in calls:
                    fn = call.get("function") or {}
                    try:
                        args = json.loads(fn.get("arguments") or "{}")
                    except json.JSONDecodeError:
                        args = {}
                    result = run_tool(fn.get("name", ""), args, ctx)
                    messages.append({"role": "tool", "tool_call_id": call.get("id") or fn.get("name", "tool"),
                                     "content": result[:12000]})
                continue
            content = (msg.get("content") or "").strip()
            if content:
                ctx.step("Answer ready")
                return content
            messages.append({"role": "user", "content":
                             "Your previous reply was empty. Produce the full structured answer now."})
        raise RuntimeError("model produced no usable answer")


# ---------------------------------------------------------------------------
# Sessions (persisted to disk)
# ---------------------------------------------------------------------------


@dataclass
class Session:
    id: str
    owner: Optional[int] = None
    title: str = "New chat"
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    messages: List[Dict[str, Any]] = field(default_factory=list)
    facts: Dict[str, str] = field(default_factory=dict)
    user_name: Optional[str] = None
    last_topic: Optional[str] = None

    def clear(self) -> None:
        self.messages.clear()
        self.facts.clear()
        self.user_name = None
        self.last_topic = None
        self.title = "New chat"

    def to_dict(self) -> Dict[str, Any]:
        return {"id": self.id, "owner": self.owner,
                "title": self.title, "created_at": self.created_at,
                "updated_at": self.updated_at, "messages": self.messages[-80:],
                "facts": self.facts, "user_name": self.user_name, "last_topic": self.last_topic}

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "Session":
        return cls(id=d["id"], owner=d.get("owner"), title=d.get("title", "New chat"),
                   created_at=d.get("created_at", time.time()), updated_at=d.get("updated_at", time.time()),
                   messages=d.get("messages", []), facts=d.get("facts", {}),
                   user_name=d.get("user_name"), last_topic=d.get("last_topic"))


class SessionStore:
    def __init__(self, path: Path = SESSIONS_FILE) -> None:
        self.path = path
        self.lock = threading.RLock()
        self.sessions: Dict[str, Session] = {}
        self._load()

    def _load(self) -> None:
        if not self.path.exists():
            return
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
            for sid, raw in data.get("sessions", {}).items():
                self.sessions[sid] = Session.from_dict(raw)
        except Exception as exc:
            print(f"[Ryzek] could not load sessions: {exc}", flush=True)

    def save(self) -> None:
        with self.lock:
            payload = {"version": 2, "sessions": {k: v.to_dict() for k, v in self.sessions.items()}}
            tmp = self.path.with_suffix(".tmp")
            tmp.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
            os.replace(tmp, self.path)

    def get(self, sid: Optional[str] = None, owner: Optional[int] = None) -> Session:
        """Sessions belong to an account. A new chat gets that account as owner,
        and an id belonging to somebody else is refused (a fresh chat is made)."""
        with self.lock:
            key = sid or str(uuid.uuid4())
            existing = self.sessions.get(key)
            if existing is not None and owner is not None and \
                    existing.owner not in (None, owner):
                key = str(uuid.uuid4())
                existing = None
            if existing is None:
                self.sessions[key] = Session(id=key, owner=owner)
            return self.sessions[key]

    def list(self, owner: Optional[int] = None) -> List[Dict[str, Any]]:
        with self.lock:
            rows = [{"id": s.id, "title": s.title, "updated_at": s.updated_at,
                     "count": len(s.messages), "created_at": s.created_at}
                    for s in self.sessions.values()
                    if owner is None or s.owner in (None, owner)]
        return sorted(rows, key=lambda r: -r["updated_at"])

    def delete(self, sid: str) -> bool:
        with self.lock:
            ok = self.sessions.pop(sid, None) is not None
        if ok:
            self.save()
        return ok

    def rename(self, sid: str, title: str) -> None:
        with self.lock:
            if sid in self.sessions:
                self.sessions[sid].title = title.strip()[:70] or "New chat"
                self.sessions[sid].updated_at = time.time()
        self.save()


class ConfigStore:
    """Server-side settings persistence (the browser also mirrors them in localStorage)."""

    def __init__(self, path: Path = CONFIG_FILE) -> None:
        self.path = path
        self.lock = threading.RLock()
        self.opts: Dict[str, Any] = q.default_opts()
        self.depth: str = DEFAULT_DEPTH
        self._load()

    def _load(self) -> None:
        if not self.path.exists():
            return
        try:
            raw = json.loads(self.path.read_text(encoding="utf-8"))
            self.opts = q.default_opts(raw.get("opts", raw))
            saved_depth = raw.get("depth")
            if saved_depth in DEPTHS:
                self.depth = saved_depth
        except Exception as exc:
            print(f"[Ryzek] could not load settings: {exc}", flush=True)

    def get(self) -> Dict[str, Any]:
        with self.lock:
            return q.default_opts(self.opts)

    def merge(self, patch: Dict[str, Any]) -> Dict[str, Any]:
        with self.lock:
            merged = q.default_opts(self.opts)
            for k, v in (patch or {}).items():
                if k == "sections" and isinstance(v, dict):
                    merged["sections"].update(v)
                elif k in merged:
                    merged[k] = v
            self.opts = q.default_opts(merged)
            self.save()
            return q.default_opts(self.opts)

    def replace(self, opts: Dict[str, Any]) -> Dict[str, Any]:
        with self.lock:
            self.opts = q.default_opts(opts)
            self.save()
            return q.default_opts(self.opts)

    def reset(self) -> Dict[str, Any]:
        with self.lock:
            self.opts = q.default_opts()
            self.depth = "exhaustive"
            self.save()
            return q.default_opts(self.opts)

    def set_depth(self, depth: str) -> str:
        with self.lock:
            if depth in DEPTHS:
                self.depth = depth
                self.save()
            return self.depth

    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.path.with_suffix(".tmp")
        tmp.write_text(json.dumps({"version": 3, "opts": self.opts,
                                   "depth": self.depth},
                                  ensure_ascii=False, indent=2), encoding="utf-8")
        os.replace(tmp, self.path)


# ---------------------------------------------------------------------------
# Quick intents + orchestrator
# ---------------------------------------------------------------------------

JOKES = [
    "Why do Python programmers wear glasses? Because they can't C.",
    "There are 10 kinds of people: those who understand binary and those who don't.",
    "A SQL query walks into a bar, approaches two tables and asks: 'May I join you?'",
    "I told my AI a secret. It said: 'Don't worry, I only use it to predict the next token.'",
]
FACTS = [
    "Octopuses have three hearts and blue, copper-based blood.",
    "A day on Venus is longer than a year on Venus.",
    "The first computer bug was a real moth stuck in a relay in 1947.",
    "Honey never spoils - edible honey has been found in ancient tombs.",
    "Bananas are botanically berries; strawberries are not.",
]

HELP_TEXT = (
    f"## {NAME} v{VERSION} - what I can do\n\n"
    "**Live research (v2.5):** for a real question I search Google News and Google Books, Google web "
    "results, Wikipedia and Simple English Wikipedia, Bing, DuckDuckGo, Wikidata, Stack Overflow, "
    "Open Library and GitHub at the same time, then open the best pages and read them. The answer is "
    "built from that material and ends with clickable links to the pages I used. The Live sources "
    "panel shows exactly which platforms answered.\n\n"
    "**Research offline too:** a curated knowledge base with BM25, full Wikipedia articles and a "
    "local cache keep working when the network does not. Every question gets a detailed answer - "
    "never a blank or an evasive non-answer.\n\n"
    "**Writing desk:** 'write an email to my teacher asking for leave', 'write an essay on climate "
    "change', 'write a letter to my friend', 'write a poem about rain', 'write a speech on teamwork', "
    "'write a python function that reverses a string' - you get the finished piece, not a description "
    "of it. Python code is deliberately short and beginner-level: one function, one example, no "
    "type hints or test harness. I also write original **Urdu ghazals and nazms** on love, hope, "
    "friendship, homeland, rain, knowledge or life, with Roman-Urdu transliteration and a plain "
    "English meaning. Try 'type urdu poetry on rain' or 'ایک غزل لکھ دو'.\n\n"
    "**Small talk:** 'hi', 'Good Morning', 'hey hw r u doin today', 'thanks', 'bye' get a short, "
    "friendly answer. Typos are understood.\n\n"
    "**Readable English:** everything is written in clear, intermediate English - short words, "
    "plain sentences, no academic padding. Change the reading level in the top bar or Settings.\n\n"
    "**Tools:** calculator with worked steps, unit conversion, date/time, persistent memory, coin, dice, "
    "random choice, local search, Wikipedia search/read, topic learning, knowledge status.\n\n"
    "**Exhaustive answers:** at `exhaustive` depth I cover the definition, mechanism, types, history, "
    "dated milestones, applications, limits, related ideas, FAQs, a glossary, sources and an honest "
    "list of what I could not verify. Every heading appears exactly once - no repeats.\n\n"
    "**Respect policy:** questions about prophets, Scriptures, religions or believers are answered "
    "with courtesy and strict neutrality. I never joke about them, never rank faiths, never take "
    "sides in sectarian disputes and never present myself as a religious authority. You can enable "
    "prophetic honorifics in Settings.\n\n"
    "**Commands:**\n"
    "- `/learn <topic>` - fetch and permanently cache a Wikipedia article\n"
    "- `/topics` - list curated topics and cached articles\n"
    "- `/depth quick|standard|deep|exhaustive` - change answer length\n"
    "- `/settings` - show the current settings summary\n"
    "- `/about` - about Ryzek AI and its creator\n"
    "- `/status`, `/sources`, `/reset`, `/help`\n"
    "- `/web` - list the live platforms Ryzek searches\n\n"
    "**Identity:** ask who my CEO, owner, boss, master, creator or developer is and I will name "
    f"**{CREATOR}** ({CREATOR_HANDLE}) directly instead of explaining what a CEO is.\n\n"
    "**Settings (gear icon):** respect mode and honorifics, grammar polish, answer style, "
    "topic breadth, plain English, auto-caching, and per-section switches for the long answer. "
    "They are saved on the server and in your browser.\n\n"
    "**Try:** 'explain black holes in detail', 'how does photosynthesis work', "
    "'what is 17% of 240', 'convert 10 km to miles', 'why is the sky blue'.\n\n"
    "**Optional:** set `RYZEK_API_KEY` for the LLM brain with an 8-step tool-calling loop. "
    "See `README.md`."
)

def creator_answer(profile: bool = False) -> str:
    """Short, person-centred answer. No tool lists, no internals, no jargon."""
    if profile:
        return (f"## {CREATOR}\n\n"
                f"**{CREATOR}**, known online as **{CREATOR_HANDLE}**, is the person who made me. He is "
                f"my CEO, owner, boss, master and creator, and he is a {CREATOR_ROLE} - very "
                "intelligent, analytical and exacting about quality.\n\n"
                "He built me in Python to answer every question properly, explain things fully, write "
                "clean English and treat prophets and religions with care. He also cares about both "
                "English and Urdu poetry, so I studied those too.\n\n"
                f"**Instagram:** [{CREATOR_INSTAGRAM}]({CREATOR_INSTAGRAM_URL})\n\n"
                "Type `/about` for the longer write-up.")
    return (f"## My CEO, master, owner and boss is {CREATOR}\n\n"
            f"I'm {NAME}, an AI made by **{CREATOR}** - also known as **{CREATOR_HANDLE}**. He is a "
            f"{CREATOR_ROLE}: very intelligent, analytical and precise. He created me, owns me, and "
            "I answer to him.\n\n"
            f"**Instagram:** [{CREATOR_INSTAGRAM}]({CREATOR_INSTAGRAM_URL})\n\n"
            "If you'd like the full story about me and him, type `/about` or open the **About** panel "
            "in the top bar. Otherwise, just ask me anything.")


def about_text() -> str:
    return (
        f"# About {NAME} v{VERSION}\n\n"
        f"## What I am\n\n{NAME} is an AI made by **{CREATOR} ({CREATOR_HANDLE})**, who is a "
        f"{CREATOR_ROLE}. He built me to answer every question properly: a short, exact fact when "
        "that is what you asked for, or a full, carefully structured explanation when you want "
        "everything. I write in clean English, I say plainly what I could not verify, and I always "
        "treat religions and prophets with respect. Every message gets a real answer - never a "
        "blank reply or a shrug.\n\n"
        "## What I can do\n\n"
        "- Explain a topic at four depths - **quick**, **standard**, **deep** and **exhaustive** - and "
        "the interface changes its accent theme with each one.\n"
        "- At exhaustive depth I cover the definition, mechanism, types, history, dated milestones, "
        "applications, limitations, related ideas, FAQs, a glossary, sources and an explicit list of "
        "what I could not verify. Headings never repeat.\n"
        "- Handle religions and prophets with courtesy and strict neutrality: no mockery, no ranking "
        "of faiths, no sectarian verdicts, no invented rulings, and optional prophetic honorifics.\n"
        "- Polish grammar, remember facts per conversation, cache whole articles for offline use, "
        "and cite the sources actually used.\n"
        "- Answer questions about English and Urdu poetry - forms, metres, movements and major poets.\n"
        "- Give the capital of a country directly and correctly, without drifting into an article "
        "about some other place.\n"
        "- Work through numbers, sequences, ordering puzzles, syllogisms and decisions with the "
        "steps shown, so you can check the reasoning yourself.\n"
        "- Remember your name, the facts you tell me and the topic we were discussing across "
        "turns in this chat - even after a server restart.\n"
        "- Cope with typos, half-finished questions and vague follow-ups like 'why?' or 'tell me more'.\n"
        "- Decline requests that could cause serious harm, while still giving you safe, useful help.\n"
        "- Chat naturally: 'hey hw r u doin today', 'hi', 'Good Morning', 'thanks' all get a warm, "
        "short reply instead of a research report.\n"
        "- **Write things for you** - a copy-ready email or letter, a structured essay, a short "
        "story, a poem, a speech, an article, a report, or a runnable Python function with tests. "
        "The finished piece comes first, then notes on how to adapt it.\n\n"
        f"## About {CREATOR}\n\n"
        f"**{CREATOR}**, aka **{CREATOR_HANDLE}**, is my creator, owner, CEO, master and boss. He is a "
        f"**{CREATOR_ROLE}** - very intelligent, analytical and exacting about quality. He asked for an "
        "assistant that answers everything, explains everything properly, respects prophets and "
        "religions, writes clean English and keeps improving. He is also interested in poetry, which is "
        f"why the poetry library exists.\n\n"
        f"- **Instagram:** [{CREATOR_INSTAGRAM}]({CREATOR_INSTAGRAM_URL})\n"
        f"- **Signature:** Made by {CREATOR.replace(' aka Ryzek', '')} aka {CREATOR_HANDLE}\n\n"
        "## Honest limits\n\n"
        "AI can also make mistakes. I mark unverified claims explicitly, I do not invent citations, "
        "and I am not a scholar, a lawyer or a religious authority. Verify anything consequential "
        "against a primary source.\n\n"
        "## Try next\n\n"
        "Ask `/help`, `/topics`, `/settings`, or a real question such as 'explain black holes in "
        "detail', 'what is a ghazal?', or 'can we do time travel?'."
    )


_CONVERT_RE = re.compile(r"\b(\d+(?:\.\d+)?)\s*([a-zA-Z°]+)\s*(?:in|to|into|as|=|->)\s*([a-zA-Z°]+)\b", re.I)
_CONVERT_RE2 = re.compile(r"\bhow many\s+([a-zA-Z°]+)\s+(?:are|is)?\s*in\s+(\d+(?:\.\d+)?)\s*([a-zA-Z°]+)", re.I)


def quick_answer(text: str, ctx: Context) -> Optional[str]:
    """Fast local intents. Returns None when the question needs research."""
    original = text.strip()
    low = original.lower()
    s = ctx.session
    greet = f", {s.user_name}" if s.user_name else ""
    # Respect gate: a religious / prophet-related message is never routed to
    # jokes, random facts or coin/dice "fun" intents. It gets a careful answer.
    religious_guard = q.respect_on(ctx.opts) and q.is_religious(original)[0]
    is_recall_question = bool(re.search(
        r"\b(do you remember|did i (?:say|tell|mention)|remind me|"
        r"what (?:did|was) (?:i|my)|what is my|what'?s my)\b", low))

    if not original or original == "(empty message)":
        return ("## I'm here\n\nYou sent an empty line, so I'll start us off. Ask me anything - a definition, "
                "a calculation, a decision, a 'why' question - and you'll get a full structured answer with sources. "
                "Type `/help` for the complete tour, or try a suggestion card below.")

    # --- Identity / ownership: checked FIRST so "who is your CEO" is never
    #     mistaken for a question about the definition of a chief executive.
    identity = (
        re.search(r"\b(?:your|ryzek(?:'s)?|the)\s+(?:ceo|chief executive(?:\s+officer)?|owner|boss|master|"
                  r"creator|founder|developer|maker|author|inventor)\b", low)
        or re.search(r"\b(?:who|what)\s+(?:is|are|was|were)?\s*(?:your|the|ryzek(?:'s)?)?\s*"
                     r"(?:ceo|chief executive(?:\s+officer)?|owner|boss|master|creator|founder|developer|maker)\b", low)
        or re.search(r"\b(?:who|what)\s+(?:built|made|created|programmed|wrote|designed|trained|owns|"
                     r"runs|founded|invented|developed)\s+(?:you|ryzek|this (?:ai|agent|bot|chatbot))\b", low)
        or re.search(r"\b(?:who\s+(?:do|are)\s+you\s+(?:belong|work|answer)\s+to|who is behind you|"
                     r"who owns you|do you have (?:a|an) (?:owner|ceo|boss|master|creator)|"
                     r"tell me about (?:your|the) (?:ceo|owner|boss|creator|maker|founder))\b", low)
    )
    if identity:
        return creator_answer()

    if re.search(r"\b(?:who is|tell me about|describe|what do you know about)\s+"
                 r"(?:rasakh|rasakh mohsin|ryzek_20|my (?:creator|owner|ceo|boss|master))\b", low):
        return creator_answer(profile=True)

    if low in ("/about", "about", "about you", "about ryzek", "who is rasakh mohsin"):
        return about_text()

    # --- Direct facts BEFORE research. A cached article about one capital
    #     must never hijack a question about a different country again.
    capital = factdb.capital_answer(original, ctx.depth)
    if capital:
        return capital
    stable_fact = factdb.quick_fact_answer(original, ctx.depth)
    if stable_fact:
        return stable_fact

    # --- Warm, natural small talk (typos included) -----------------------
    # "hey hw r u doin today", "hi", "Good Morning", "thanks", "bye" are
    # real messages. They get a short human reply, never a research scaffold.
    small = chat.smalltalk(original, ctx.depth, s.user_name or "")
    if small:
        return small

    if re.search(r"\b(who are you|what are you|your name|introduce yourself)\b", low):
        return (f"## I'm {NAME}\n\n"
                f"I'm an AI made by **{CREATOR}** - also known as **{CREATOR_HANDLE}** - who is a "
                f"{CREATOR_ROLE}. I answer every question in as much detail as you want, from a quick "
                "fact to a full explanation, and I always treat religions and prophets with respect.\n\n"
                "Ask me anything at all. Type `/about` if you'd like the longer story.")

    if re.search(r"\b(who (made|created|built|programmed|wrote) you|your (creator|developer|maker))\b", low):
        return (f"## You did\n\nI'm {NAME}, the Python agent you built. Everything is editable in this folder - "
                "there is no hidden service.\n\n"
                "## Where each part lives\n\n"
                "- `ryzek_core.py` - retrieval index, research pipeline, tool registry, LLM loop, memory.\n"
                "- `ryzek_ai.py` - HTTP server, streaming API and terminal chat.\n"
                "- `ryzek_ui.py` - the entire web interface (inline CSS/JS, no build step).\n"
                "- `knowledge_base.json` - what I know offline; add an entry and restart.\n\n"
                "## Why that matters\n\nBecause you own the code, you can change my personality in `SYSTEM_PROMPT`, add a tool with one "
                "`@tool` decorator, or point me at a different model with one environment variable.")

    if low in ("/help", "help", "what can you do", "commands", "/commands"):
        return HELP_TEXT

    if low in ("/status", "status"):
        return (f"## Status\n\n- **Engine:** {'LLM (' + LLMAgent().model + ')' if LLMAgent().enabled else 'offline research brain'}\n"
                f"- **Curated topics:** {len(KB)}\n- **Cached articles:** {cached_count()}\n"
                f"- **Indexed chunks:** {len(INDEX.chunks)}\n- **Tools:** {len(TOOL_REGISTRY)}\n"
                f"- **Live research:** {'on' if (ONLINE and ctx.online) else 'off'}\n"
                f"- **Answer depth:** {ctx.depth}\n- **Sessions on disk:** {SESSIONS_FILE}")

    if low in ("/settings", "settings"):
        o = q.default_opts(ctx.opts)
        sec = ", ".join(k for k, v in o["sections"].items() if v) or "none"
        return ("## Current settings\n\n"
                f"- **Respect policy:** {'on' if q.respect_on(o) else 'off'} "
                f"(mode: {o['respect_mode']}, honorifics: {o['honorifics']})\n"
                f"- **Grammar polish:** {'on' if o['grammar'] else 'off'}\n"
                f"- **Answer style:** {o['style']}\n"
                f"- **Source breadth:** {o['breadth']} article(s) per question\n"
                f"- **Plain English:** {'on' if o['simple_english'] else 'off'}\n"
                f"- **Reading level:** {plain.label(o.get('english_level', 'intermediate'))}\n"
                f"- **Live web platforms:** {len(web.PLATFORMS)}\n"
                f"- **Auto-cache articles:** {'on' if o['auto_learn'] else 'off'}\n"
                f"- **Long-answer sections enabled:** {sec}\n\n"
                "Open the gear icon to change these. They are stored in `data/config.json` on the "
                "server and mirrored in this browser's local storage, so they survive restarts.")

    if low.startswith("/depth"):
        return None  # handled by the orchestrator

    if low.startswith("/learn") or low.startswith("learn "):
        return None  # handled by the orchestrator

    if low in ("/topics", "topics", "list topics"):
        names = [t["title"] for t in KB]
        cached = []
        for p in sorted(LEARNED_DIR.glob("*.json"))[-12:]:
            try:
                cached.append(json.loads(p.read_text(encoding="utf-8"))["title"])
            except Exception:
                pass
        return ("## Knowledge inventory\n\n**Curated topics (" + str(len(names)) + "):**\n" +
                "\n".join(f"- {n}" for n in names) +
                "\n\n**Recently cached Wikipedia articles (" + str(cached_count()) + " total):**\n" +
                ("\n".join(f"- {c}" for c in cached) or "- none yet - ask me a factual question and I'll cache one") +
                "\n\nAdd your own by editing `knowledge_base.json`, or use `/learn <topic>`.")

    if low in ("/web", "web sources", "live sources", "platforms"):
        rows = "\n".join(
            f"- **{p['label']}** - {p['desc']}" for p in web.PLATFORMS)
        return ("## Live web platforms\n\n"
                "For a real question I query all of these in parallel, read the best pages and "
                "cite the ones I used. A platform that refuses the request is reported honestly "
                "in the Live sources panel instead of being quietly skipped.\n\n" + rows +
                "\n\n## Latest sweep\n\n" +
                (f"Last query: `{web.last_status()['query']}`" if web.last_status()["query"]
                 else "No live search yet in this session - ask me a factual question."))

    if low in ("/sources", "sources"):
        last = next((m for m in reversed(s.messages) if m.get("sources")), None)
        if last and any(x.get("url") for x in last["sources"]):
            links = "\n".join(f"- [{x['title']}]({x['url']}) - {x['kind']}" for x in last["sources"] if x.get("url"))
        else:
            links = "- No external links in the most recent answer. Instant skills (maths, clock, memory, small talk) answer from local logic and say so."
        return ("## Sources for the last answer\n\n" + links + "\n\n"
                "## How sourcing works\n\n- Every researched answer searches the curated base and Wikipedia, then lists the articles it read.\n"
                "- Cached articles are reused with zero network calls; they are labelled `cached article` or `further reading`.\n"
                "- If I could not verify something, that appears in the **What I could not verify** section - I never invent a citation.\n"
                "- Source chips appear under each bot message when the Sources toggle is on in Settings.")

    if low in ("/reset", "reset", "clear chat", "start over", "forget everything"):
        return None  # handled by orchestrator

    m = re.search(r"\b(?:my name is|call me|i go by|i'm known as)\s+([A-Za-z][A-Za-z'-]{1,24})\b", original, re.I)
    if not m:
        m = re.fullmatch(r"(?:i am|i'm)\s+([A-Za-z][A-Za-z'-]{1,24})[.!?\s]*", original.strip(), re.I)
    if m:
        s.user_name = m.group(1).strip().title()
        s.facts["user_name"] = s.user_name
        return (f"## Got it - {s.user_name}\n\nI've saved your name in this chat's persistent memory, "
                "so it survives a server restart. What shall we dig into? I can research a topic in depth, "
                "work through a calculation, or compare two options properly.")

    if re.search(r"\b(what.?s my name|whats my name|what is my name|who am i|do you remember my name)\b", low):
        if s.user_name:
            return (f"## You're {s.user_name}\n\nI saved that in this conversation's memory.\n\n"
                    "## How I remember\n\n- Your name is stored in `data/sessions.json` alongside the chat history, so it survives a server restart.\n"
                    "- It is scoped to this conversation; a new chat starts with a clean memory.\n"
                    "- Send `/reset` to clear it, or `call me <new name>` to overwrite it.\n\n"
                    "I deliberately don't guess names I was never given - that would be inventing a fact.")
        return (f"## You're {CREATOR}\n\n"
                f"You are **{CREATOR}** - also **{CREATOR_HANDLE}** - my creator, owner, CEO, master and "
                f"boss, and a {CREATOR_ROLE}. You're very intelligent, analytical, and you built me in "
                "Python to answer every question thoroughly and respectfully.\n\n"
                "## If someone else is using this chat\n\n"
                "Say `call me <name>` and I'll remember that name for this conversation instead. "
                "Your identity as my creator is stored in my configuration and never changes; the "
                "saved name is only a per-chat convenience.\n\n"
                f"Instagram: [{CREATOR_INSTAGRAM}]({CREATOR_INSTAGRAM_URL}). Type `/about` for the full page.")

    m = re.search(r"\b(?:remember|note down|keep in mind)\s+(?:that\s+)?(.+)", original, re.I)
    if m and not is_recall_question and len(m.group(1).strip()) > 3:
        fact = m.group(1).strip().rstrip(".!")[:220]
        key = re.sub(r"[^a-z0-9]+", "_", fact.lower()).strip("_")[:45] or "note"
        s.facts[key] = fact
        return (f"## Saved\n\n> {fact}\n\nStored under `{key}`.\n\n"
                "## What happens now\n\n- The fact is written to disk immediately and survives restarts.\n"
                "- `what do you remember` reads it back; the LLM brain can also call the `recall` tool.\n"
                "- `/reset` clears all saved facts and the chat history.\n\n"
                "I store exactly what you said - I don't reinterpret or embellish it.")

    if re.search(r"\b(what do you remember|what have i told you|show (my )?(memory|facts)|list (my )?facts)\b", low):
        saved_facts = [v for k, v in s.facts.items() if k != "user_name"]
        return ("## Memory for this chat\n\n" +
                (f"- Your name: {s.user_name}\n" if s.user_name else "") +
                ("\n".join(f"- {v}" for v in saved_facts[-12:]) if saved_facts else "- Nothing else saved yet. Say `remember that <something>`.") +
                "\n\n## Details\n\n- Memory is per conversation and persisted to `data/sessions.json` with atomic writes.\n"
                "- It does not leak between chats, and `/reset` wipes it.\n"
                "- Unlike the knowledge base, these are user facts, not general information - I never treat them as sources.")

    # --- Recall ONE specific remembered detail across turns ----------------
    if is_recall_question:
        qwords = set(tokens(low)) - {
            "remember", "remind", "did", "say", "told", "tell", "mention", "what",
            "was", "were", "my", "favourite", "favorite", "please", "about", "again",
            "you", "the", "is", "it", "name"}
        best = None
        for key, value in s.facts.items():
            if key == "user_name":
                continue
            overlap = len(qwords & set(tokens(key + " " + value)))
            if overlap and (best is None or overlap > best[0]):
                best = (overlap, key, value)
        if best:
            return (f"## Yes, I remember\n\n> {best[2]}\n\n"
                    "You told me that earlier in this conversation. It is stored with this chat's "
                    f"memory under `{best[1]}`, so it survives a server restart.\n\n"
                    "## What else persists\n\n"
                    "- Your saved name and every `remember that ...` note stay with this chat.\n"
                    "- `/reset` clears them; a new chat starts clean.\n"
                    "- I treat these as facts about you, not as sources for general claims.\n\n"
                    "Ask me to use that detail in an answer and I will.")

    # A question about the clock/calendar only. "time travel", "time machine",
    # "time dilation", "space-time" etc. must go to research, not the clock.
    clock_question = bool(
        re.search(r"\b(what time is it|what'?s the time|current time|current date|"
                  r"today'?s date|what day is it|what is (?:the )?(?:date|time) today|"
                  r"tell me the (?:time|date)|the date today)\b", low)
        or re.fullmatch(r"\s*(?:time|date|today|what day|what is today)\s*[?.!]?\s*", low)
    )
    clock_question = clock_question and not re.search(
        r"time travel|time machine|time dilation|space.?time|time complexity|real.?time|"
        r"long time|runtime|time series|time management|part.?time", low)
    if clock_question:
        now = current_time()
        return (f"## Date and time\n\n**{now}**\n\n"
                "## How I got it\n\nI read the system clock of the machine running this app and formatted it "
                "with the local timezone. Set `RYZEK_TZ=Asia/Karachi` (or any IANA zone) to pin a specific region; "
                "otherwise the host's zone is used.\n\n"
                "## Worth knowing\n\n- 'Now' differs by timezone and by daylight-saving rules.\n"
                "- For scheduling across regions, store UTC internally and convert only at display time.\n"
                "- If you need an exact historical or future date calculation, tell me the two dates and I'll work it out.\n\n"
                "## Sources\n\n- Local system clock (no external time server queried).")

    if not religious_guard and re.search(r"\b(joke|make me laugh|something funny|tell me a joke)\b", low):
        return ("## A joke for you\n\n" + random.choice(JOKES) +
                "\n\n## Why it works\n\nIt's a small pun on programming syntax - the kind of humour that only "
                "lands if you know the language. Yes, I answer the silly questions in detail too.")

    if not religious_guard and re.search(r"\b(fun fact|random fact|interesting fact|tell me something|surprise me)\b", low):
        return ("## Something interesting\n\n" + random.choice(FACTS) +
                "\n\n## Want the full story?\n\nGive me that topic as a question and I'll research it with sources "
                "instead of handing you a one-liner.")

    if not religious_guard and re.search(r"\b(flip (a )?coin|heads or tails|toss a coin)\b", low):
        return ("## Coin flip\n\n**" + random.choice(["Heads", "Tails"]) + "**\n\n"
                "## The maths\n\n- A fair coin has P(Heads) = P(Tails) = 0.5, and the two outcomes are mutually exclusive and exhaustive.\n"
                "- Flips are independent: a run of five heads does not make tails more likely next (that belief is the gambler's fallacy).\n"
                "- For n flips, the number of heads follows a binomial distribution with mean n/2 and variance n/4.\n\n"
                "## Try next\n\nAsk for best of three, or say 'explain probability in detail' for a full sourced answer. Best of three?")

    m = re.search(r"\broll(?: a)?(?: (\d+))?\s*(?:d\s*(\d+))?", low)
    if m and not religious_guard:
        if m.group(2):
            sides, count = int(m.group(2)), int(m.group(1) or 1)
        elif m.group(1) and "dice" in low:
            sides, count = 6, int(m.group(1))
        else:
            sides, count = int(m.group(1) or 6), 1
        roll = run_tool("roll_dice", {"sides": sides, "count": count}, ctx)
        return ("## Dice roll\n\n" + roll + "\n\n"
                f"## The maths\n\n- Each d{sides} is uniform over 1..{sides}, so a single face has probability 1/{sides}.\n"
                f"- The expected value of one die is (1 + {sides})/2 = {(1 + sides) / 2:g}; for {count} dice the expected total is {count * (1 + sides) / 2:g}.\n"
                "- Dice are independent, so totals cluster around the middle rather than the extremes.\n\n"
                "## Try next\n\nAsk me to compare two options properly instead - I'll research a real recommendation.")

    m = re.search(r"\b(?:pick|choose|decide)\b.*?(?:between|from|of|:)?\s*(.+)", original, re.I)
    if m and not religious_guard and re.search(r",|\bor\b|\bvs\b|\|", m.group(1), re.I):
        return ("## Decision\n\n" + run_tool("pick_one", {"options": m.group(1)}, ctx) + "\n\n"
                "## Important caveat\n\nThat is a **random tie-break**, not a recommendation. A real decision should be made on criteria, "
                "not chance.\n\n"
                "## A better method\n\n1. Name the two or three things that actually matter (cost, time, risk, reversibility).\n"
                "2. Score each option against them, then check which score depends on an assumption you haven't verified.\n"
                "3. If the downside is small and reversible, pick and move on; if it is large and permanent, gather one more data point.\n\n"
                "Give me your criteria and the options, and I'll research a proper structured comparison instead.")

    # Maths - detailed worked solution
    has_digit = bool(re.search(r"\d", original))
    mathy = has_digit and re.search(
        r"[\+\-\*\/\^\%×÷]|plus|minus|times|divided|multiplied|power|squared|cubed|percent|%|\bof\b|calculate|compute|solve|evaluate",
        original, re.I)
    if mathy:
        try:
            return detailed_math(original)
        except Exception:
            pass

    for pattern in (_CONVERT_RE, _CONVERT_RE2):
        cm = pattern.search(original)
        if cm:
            try:
                if pattern is _CONVERT_RE:
                    return detailed_conversion(cm.group(1), cm.group(2), cm.group(3))
                return detailed_conversion(cm.group(2), cm.group(3), cm.group(1))
            except (ValueError, KeyError):
                continue

    return None


@dataclass
class Reply:
    text: str
    engine: str
    note: str = ""
    trace: List[Dict[str, str]] = field(default_factory=list)
    sources: List[Dict[str, str]] = field(default_factory=list)
    elapsed: float = 0.0
    session_id: str = ""
    depth: str = "deep"
    web_status: List[Dict[str, Any]] = field(default_factory=list)
    understanding: Dict[str, Any] = field(default_factory=dict)


# Short, under-specified follow-ups inherit the topic of the previous turn.
_FOLLOWUP_PATTERNS = [
    r"^(?:why|how|what|when|where|who|which|really|ok\??|okay)\??$",
    r"^(?:tell me more|explain more|more detail|more|continue|go on|and\??|then\??|"
    r"what else\??|why\??|how\??|expand(?: on)?(?: that| it)?|elaborate)\??$",
    r"^(?:what|how|why) about (?:it|that|this|them|the same)\??$",
    r"^(?:give|show) (?:me )?(?:an? )?example\??$",
    r"^(?:is|are|was|were|can|could|does|do|did) (?:it|that|this|they)\b.{0,60}\??$",
    r"^(?:and|what about|how about)\s+[A-Za-z .'-]{2,26}\??$",
    r"^(?:its|it's)\s+.{0,36}\??$",
]
_FOLLOWUP_RE = [re.compile(p, re.I) for p in _FOLLOWUP_PATTERNS]


def resolve_followup(text: str, session: "Session") -> Tuple[str, str]:
    """Return (effective question, short continuity note)."""
    clean = (text or "").strip()
    if not getattr(session, "last_topic", ""):
        return clean, ""
    if not any(r.match(clean) for r in _FOLLOWUP_RE):
        return clean, ""
    topic = session.last_topic
    return f"{clean} about {topic}", (
        f"*Continuing our discussion of **{topic}** - I kept that context from your earlier "
        "question in this chat.*")


def writing_material(topic: str, ctx: Optional["Context"] = None) -> List[str]:
    """Real, checkable sentences about a topic for the writing desk.

    v2.5: a checked definition from the curated base opens the piece, then
    sentences from the live pages Ryzek fetched, then the remaining local
    material. An essay therefore says what the subject IS before quoting a
    news result, and still contains genuinely fresh web facts.
    """
    out: List[str] = []
    curated: List[str] = []
    t = topic_lookup(topic or "")
    if t:
        body = t.get("summary", "") + "\n\n" + "\n\n".join(
            sec.get("text", "") for sec in t.get("sections", []))
        for raw in sentences(q.clean_wiki(body)):
            line = q.clean_sentence(raw)
            if 50 <= len(line) <= 320 and not line.startswith("="):
                curated.append(line)
        for line in curated[:2]:
            if re.search(r"\b(refers to|is a |is the |are |means )", line, re.I):
                out.append(line)
                break
    # Live web material next (Google, Bing, DuckDuckGo, Wikipedia, pages).
    if ctx is not None and ctx.web_items:
        out.extend(web.material_sentences(ctx.web_items, max_items=10)[:16])
    if len(out) < 10:
        with INDEX_LOCK:
            hits = INDEX.search(topic or "", k=8)
        for h in hits:
            for raw in sentences(q.clean_wiki(h.get("text", ""))):
                line = q.clean_sentence(raw)
                if 50 <= len(line) <= 320 and not line.startswith("="):
                    curated.append(line)
    out.extend(curated)
    seen, result = set(), []
    for line in out:
        key = line[:60].lower()
        if key in seen:
            continue
        seen.add(key)
        result.append(line.rstrip(".") + "." if not line.endswith((".", "!", "?")) else line)
        if len(result) >= 26:
            break
    return result


class Ryzek:
    def __init__(self) -> None:
        self.llm = LLMAgent()
        self.store = SessionStore()
        self.config = ConfigStore()
        self.memory = memory_kit.shared_memory()
        self.auth = auth_kit.AUTH
        self.guard = auth_kit.SignupGuard(self.auth.db)

    @property
    def engine(self) -> str:
        return "llm" if self.llm.enabled else "offline"

    def status(self) -> Dict[str, Any]:
        with INDEX_LOCK:
            chunks = len(INDEX.chunks)
        return {"name": NAME, "version": VERSION, "engine": self.engine,
                "model": self.llm.model if self.llm.enabled else "offline research brain",
                "tools": len(TOOL_REGISTRY), "topics": len(KB), "cached": cached_count(),
                "chunks": chunks, "online": ONLINE, "depth": DEFAULT_DEPTH,
                "web_platforms": len(web.PLATFORMS),
                "sessions": len(self.store.sessions), "settings": self.config.get()}

    def respond(self, message: str, session: Session,
                depth: Optional[str] = None,
                online: Optional[bool] = None,
                opts: Optional[Dict[str, Any]] = None,
                emit: Optional[Callable[[Dict[str, Any]], None]] = None,
                user: Optional[Dict[str, Any]] = None) -> Reply:
        t0 = time.time()
        text = normalise_question((message or "").strip())
        if not text:
            text = "(empty message)"
        low = text.lower()
        use_depth = depth if depth in DEPTHS else DEFAULT_DEPTH
        ctx = Context(session=session, depth=use_depth,
                      online=ONLINE if online is None else online, emit=emit,
                      opts=q.default_opts(opts if opts is not None else self.config.get()),
                      user=user, memory=self.memory)

        # --- v2.6: understand first, then recall, then answer ----------------
        u = understand.analyze(text, session)
        ctx.understanding = u
        ctx.step("Understanding what you mean",
                 " · ".join(u.plan[:3]) or u.intent)
        if u.is_followup:
            ctx.step("Reading earlier messages",
                     str(getattr(session, "last_topic", "") or "")[:90])

        # --- v2.6: memory -------------------------------------------------
        mem = self.memory
        uid = ctx.user_id
        # Everything the user says can teach the memory ("my name is Ali").
        try:
            # "remember that my exam is on 12 May" -> store the subject AND a
            # session-level fact so the memory is visible everywhere.
            note = None
            m = re.match(r"^(?:please\s+)?remember\s+(?:that\s+)?(.+)$", text, re.I)
            if m:
                note = m.group(1).strip()
            learned = mem.learn_from_message(uid, text)
            if note:
                key = "note_" + str(len(session.facts) + 1)
                mem.remember_fact(uid, key, note, "told me to remember it")
                session.facts[key] = note
                learned.append(key)
            if learned:
                ctx.step("Remembering", ", ".join(learned))
                if "name" in learned:
                    session.user_name = mem.get_fact(uid, "name") or session.user_name
                for key in learned:
                    val = mem.get_fact(uid, key)
                    if val:
                        session.facts[key] = val
        except Exception:
            pass

        if low in ("/forget", "forget me", "forget everything about me",
                   "delete my memory", "clear my memory"):
            mem.clear(uid)
            session.facts.clear()
            session.user_name = None
            return Reply("## Memory cleared\n\nI removed every saved fact and every "
                         "stored question from this account. Your chats are still in the "
                         "sidebar, but I will not use them as memory any more.",
                         self.engine, session_id=session.id, depth=use_depth)

        # Questions about the person, or about what they asked before.
        if u.intent == "personal" and not any(
                r.match(low) for r in _FOLLOWUP_RE):
            facts = mem.all_facts(uid, limit=20)
            key = understand.personal_query(text)
            rows = []
            if key:
                found = [f for f in facts if f["key"] == key]
                if found:
                    facts = found + [f for f in facts if f["key"] != key]
            if not key:
                rows = mem.recent_questions(uid, limit=8)
            ctx.step("Searching my memory of you",
                     f"{len(facts)} saved facts · {len(rows)} stored questions")
            body = answer_kit.build_memory_answer(u, facts, rows, session.user_name)
            return self._finish(text, body, ctx, t0, "memory")

        # --- commands -----------------------------------------------------
        if low in ("/reset", "reset", "clear chat", "start over"):
            session.clear()
            self.store.save()
            return Reply("## Fresh start\n\nHistory and memory cleared. Every question still gets a full answer - fire away.",
                         self.engine, session_id=session.id, depth=use_depth)

        if low.startswith("/depth"):
            parts = low.split()
            if len(parts) > 1 and parts[1] in DEPTHS:
                ctx.depth = parts[1]
                use_depth = ctx.depth
                return Reply(f"## Depth set to **{use_depth}**\n\n"
                             "- `quick` - short structured answer\n"
                             "- `standard` - moderate detail\n"
                             "- `deep` - long, multi-source answer\n"
                             "- `exhaustive` - everything about the topic (default)",
                             self.engine, session_id=session.id, depth=use_depth)
            return Reply("## Depth options\n\n`/depth quick`, `/depth standard`, "
                         "`/depth deep`, `/depth exhaustive`",
                         self.engine, session_id=session.id, depth=use_depth)

        if low.startswith("/learn") or low.startswith("learn "):
            topic = re.sub(r"^(/learn|learn)\s*", "", text, flags=re.I).strip()
            if not topic:
                return Reply("## Teach me a topic\n\nUsage: `/learn photosynthesis` - I fetch the full "
                             "Wikipedia article and cache it locally for offline answers.",
                             self.engine, session_id=session.id, depth=use_depth)
            answer = learn_topic(topic, ctx)
            return self._finish(text, answer, ctx, t0, "offline")

        # --- v2.6.3: poetry by a named poet is a recital, not a question ---
        # Handled here (in respond) rather than in synthesize() so it never has
        # to fight the "answer is too short" guards downstream.
        if poetry_kit.wants_poetry(text):
            poet = poetry_kit.find_poet(text)
            if poet:
                ctx.step("Opening the poetry shelf", poetry_kit.POETS[poet]["title"])
                body = poetry_kit.recite(poet, text)
                return self._finish(text, body, ctx, t0, "poetry")
            if re.search(r"\b(of|by|ka|ki)\b", low) and \
                    re.search(r"\b(tell|recite|give|sunao|suna|koi)\b", low):
                return Reply(poetry_kit.list_poets(), self.engine,
                             session_id=session.id, depth=use_depth)

        # --- safety guardrails -------------------------------------------
        # Still a full, substantive answer: a clear refusal plus safe help.
        safe = safety.check(text)
        if safe:
            ctx.step("Safety guardrail", "declined harmful instructions, offered safe alternatives")
            return self._finish(text, safe, ctx, t0, "safety")

        # --- multi-turn continuity ---------------------------------------
        effective_text, prefix = resolve_followup(text, session)
        if prefix:
            ctx.step("Using conversation context", session.last_topic)

        # --- quick local intents -----------------------------------------
        quick = quick_answer(text, ctx)
        engine, note = "offline", ""
        if quick is None:
            # Detect the writing task first: a web search must use the TOPIC
            # ("climate change"), not the instruction ("type essay on ..."),
            # otherwise the engines return essay-writing websites instead of
            # facts about the subject.
            wmeta = writing.detect(text)
            needs_web = (wmeta is None) or wmeta["genre"] in ("essay", "article", "speech", "report")

            # --- LIVE WEB RESEARCH (v2.5) --------------------------------
            # One parallel sweep feeds BOTH the writing desk and the research
            # composer. Small talk, maths, identity, memory, code and creative
            # writing stay local and make no network call.
            if ctx.online and ONLINE and needs_web:
                try:
                    # v2.6: search the SUBJECT the user meant, not the sentence.
                    query = ((wmeta["topic"] if wmeta else None)
                             or (u.subject if u.subject else None)
                             or effective_text)
                    bundle = web.gather(query, limit=12)
                    ctx.web_items = bundle["items"]
                    ctx.web_status = bundle["status"]
                    ok = sum(1 for x in bundle["status"] if x["ok"])
                    ctx.step("Searching live platforms",
                             f"{ok} platforms · {len(ctx.web_items)} results · Google, Bing, "
                             "DuckDuckGo, Wikipedia + more")
                    for it in ctx.web_items[:8]:
                        if any(x.get("url") == it["url"] for x in ctx.sources):
                            continue
                        ctx.sources.append({"title": it["title"], "url": it["url"],
                                            "kind": it["source"], "excerpt": it["snippet"][:220]})
                except Exception as exc:
                    ctx.step("Live web unavailable", type(exc).__name__)
            # Real writing: emails, essays, letters, stories, poems, reports,
            # Urdu ghazals and simple Python functions - the piece comes first.
            material = writing_material(wmeta["topic"], ctx=ctx) if wmeta else None
            if material:
                ctx.step("Gathering real material", f"{len(material)} checked sentences for the draft")
            quick = writing.write(text, ctx.depth, material=material,
                                  sources=ctx.web_items[:6])
            if quick:
                ctx.step("Writing the piece", "drafted a complete, copy-ready answer")
        reasoned = None
        if quick is None:
            reasoned = reason.solve(text, ctx.depth)
        if reasoned:
            ctx.step("Numerical / logical / analytical reasoning", "deterministic solver")
            quick, engine = reasoned, "offline"
        elif quick is None and self.llm.enabled:
            ctx.step("Planning with the LLM brain", self.llm.model)
            try:
                answer = self.llm.respond(effective_text, ctx)
                quick = answer
                engine = "llm"
                note = ""
            except Exception as exc:  # noqa: BLE001
                ctx.step("LLM unavailable, using research brain", type(exc).__name__)
                note = f"LLM unavailable ({type(exc).__name__}) - answered with the offline research brain."
                engine = "offline"
        if quick is not None:
            return self._finish(text, quick, ctx, t0, engine, note, prefix)

        # --- full research pipeline (v2.6: understand -> synthesise) ------
        try:
            research(effective_text, ctx)          # retrieval + live pages only
        except Exception as exc:  # retrieval problems must not break the reply
            ctx.step("Retrieval problem", type(exc).__name__)
        written = None
        try:
            written = synthesize(effective_text, ctx)
        except Exception as exc:
            ctx.step("Composer problem", type(exc).__name__)
        if not written:
            # No trustworthy material: say so briefly instead of a fake framework.
            written = answer_kit.honest_fallback(u, ctx.depth)
            ctx.step("Telling you honestly what is missing", "no usable source")
        return self._finish(text, written, ctx, t0, "offline", note or ctx.note, prefix)

    def _finish(self, user_text: str, answer: str, ctx: Context, t0: float,
                engine: str, note: str = "", prefix: str = "") -> Reply:
        # Single choke point: respect note, honorifics, grammar pass, heading dedupe.
        # Applies to quick intents, researched answers, LLM output and fallbacks.
        answer = q.finalize_answer(answer, user_text, ctx.opts)
        answer = plain.intermediate(answer, ctx.opts.get("english_level", "intermediate"))
        if prefix:
            answer = prefix + "\n\n" + answer
        s = ctx.session
        now = time.time()
        # Remember the active topic so short follow-ups ("why?", "tell me more")
        # keep working in this session, including after a server restart.
        if prefix:
            # A bare "why?" / "tell me more" must not replace the topic it
            # refers to. Keep the previous turn's subject for the next one.
            pass
        elif any(st.get("label") in ("Ranking passages", "Reading source",
                                    "Numerical / logical / analytical reasoning",
                                    "Using conversation context") for st in ctx.steps):
            t = topic_lookup(user_text)
            s.last_topic = t["title"] if t else " ".join(user_text.split())[:70]
        s.messages.append({"role": "user", "content": user_text, "ts": now})
        s.messages.append({"role": "assistant", "content": answer, "ts": now,
                           "sources": ctx.sources[-8:], "trace": ctx.steps[-20:],
                           "engine": engine, "depth": ctx.depth,
                           "elapsed": round(time.time() - t0, 2), "note": note,
                           "web": ctx.web_status})
        s.messages = s.messages[-80:]
        s.updated_at = now
        # v2.6: remember the question and what Ryzek understood it to be about.
        try:
            if self.memory is not None:
                topic = ""
                if ctx.understanding is not None:
                    topic = (getattr(ctx.understanding, "subject", "")
                             or getattr(ctx.understanding, "intent", ""))
                self.memory.log_question(ctx.user_id, s.id, user_text, answer, topic)
                if not prefix and ctx.understanding is not None and \
                        getattr(ctx.understanding, "subject", ""):
                    s.last_topic = ctx.understanding.subject
        except Exception:
            pass
        if s.title == "New chat" and user_text not in ("(empty message)",):
            s.title = " ".join(user_text.split())[:52] + ("..." if len(user_text) > 52 else "")
        self.store.save()
        reply = Reply(text=answer, engine=engine, note=note, trace=ctx.steps[-20:],
                      sources=ctx.sources[-8:], elapsed=round(time.time() - t0, 2),
                      session_id=s.id, depth=ctx.depth, web_status=ctx.web_status,
                      understanding=(ctx.understanding.as_dict()
                                     if ctx.understanding is not None else {}))
        if ctx.emit:
            try:
                ctx.emit({"type": "final", "reply": reply.text, "engine": reply.engine,
                          "note": reply.note, "sources": reply.sources,
                          "trace": reply.trace, "elapsed": reply.elapsed,
                          "session_id": reply.session_id, "depth": reply.depth,
                          "title": s.title, "web": reply.web_status,
                          "understanding": reply.understanding})
            except Exception:
                pass
        return reply
