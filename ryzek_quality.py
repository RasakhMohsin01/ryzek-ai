#!/usr/bin/env python3
"""
Ryzek AI v2.1 - answer quality, religious/prophetic etiquette, and the
exhaustive explanation composer.

Self-contained: this module does NOT import ryzek_core (core imports it), so
there is no circular dependency. Everything here is pure stdlib.

Responsibilities:
  * clean_wiki()      - repair Wikipedia plaintext (headings, references, wrapped lines)
  * clean_sentence()  - fix comma splices, spacing, fragments, capitalisation
  * polish_text()     - full-answer grammar pass + global heading de-duplication
  * respect layer     - detect religious topics, add honorifics and a courtesy note
  * compose_answer()  - build a long, non-repeating, fully sourced explanation
  * finalize_answer() - single choke point applied to EVERY answer
"""

from __future__ import annotations

import re
from collections import Counter
from typing import Any, Dict, List, Optional, Tuple

NAME = "Ryzek AI"

STOPWORDS = set("""a an the and or of to in on for with is are was were be been being it its this that these those
as at by from into about over under than then so if but not no do does did doing have has had having i you he she
they we me my your our their them him her who whom what which when where why how can could should would will shall
may might must please tell explain define describe give show make want need answer question me more very also just
there here such each other any some all one two three using used use""".split())


# ---------------------------------------------------------------------------
# Token / sentence helpers
# ---------------------------------------------------------------------------


def tokens(text: str) -> List[str]:
    out = []
    for w in re.findall(r"[a-z0-9]+", (text or "").lower()):
        if len(w) <= 2 or w in STOPWORDS:
            continue
        if len(w) > 4 and w.endswith("s") and not w.endswith("ss"):
            w = w[:-1]
        out.append(w)
    return out


def sentences(text: str) -> List[str]:
    return [s.strip() for s in re.split(r"(?<=[.!?])\s+", (text or "").strip()) if s.strip()]


REF_RE = re.compile(
    r"\b(?:ISBN|doi\s*:|PMID|JSTOR|OCLC|Retrieved|Archived|Wayback Machine|"
    r"citation needed|pdf|Lecture|lecture|Press\.|University Press|Vol\.|pp\.)\b"
    r"|https?://|www\."
    r"|^[A-Z][a-z]+,\s+[A-Z]\.?\s.*\(\d{4}\)",
    re.IGNORECASE,
)


def clean_wiki(text: str) -> str:
    """Repair a Wikipedia plaintext extract.

    Removes section markers, standalone section headings, reference/citation
    debris, and rejoins lines that were wrapped inside one paragraph. This is
    the single biggest source of the old grammar/fragment problems.
    """
    lines: List[str] = []
    for raw in (text or "").splitlines():
        s = raw.strip()
        if not s:
            lines.append("")
            continue
        if re.match(r"^=+.*=+$", s):                       # === Heading ===
            continue
        if s.endswith(":") and len(s.split()) <= 5:          # stray label
            continue
        if len(s.split()) <= 5 and not re.search(r"[.!?]$", s):
            continue                                          # bare section heading
        lines.append(s)

    paras: List[str] = []
    buf: List[str] = []
    for s in lines:
        if not s:
            if buf:
                paras.append(" ".join(buf))
                buf = []
        else:
            buf.append(s)
    if buf:
        paras.append(" ".join(buf))

    # Remove bibliography / "further reading" debris that Wikipedia extracts
    # leave inside otherwise good paragraphs. This is what used to produce
    # strings like "Pesic, Peter (2005). Sky in a Bottle. The MIT Press. ISBN..."
    scrubbed: List[str] = []
    for p in paras:
        parts = [x.strip() for x in re.split(r"(?<=[.!?])\s+", p) if x.strip()]
        keep = []
        for piece in parts:
            if REF_RE.search(piece):
                continue
            if len(piece) < 22:
                continue
            if piece.endswith("?") and len(piece.split()) <= 7:
                continue
            if re.match(r"^(?:Dr|Prof|Mr|Mrs|Ms)\s*\.", piece):
                continue
            keep.append(piece)
        if keep:
            scrubbed.append(" ".join(keep))
    out = re.sub(r"\[\s*\d+\s*\]", "", "\n\n".join(scrubbed))
    out = re.sub(r"\[citation needed\]", "", out, flags=re.I)
    return re.sub(r"[ \t]{2,}", " ", out).strip()


def clean_sentence(s: str) -> str:
    """Fix the most common mechanical grammar faults in one sentence/line."""
    s = re.sub(r"\s+", " ", (s or "")).strip()
    if not s:
        return ""
    s = re.sub(r"\s+([,.!?;:])", r"\1", s)          # "word ," -> "word,"
    s = re.sub(r"([,;:])\s*([.!?])", r"\2", s)      # "word,." -> "word."
    s = re.sub(r"\.{3,}", "…", s)                 # keep real ellipses intact
    s = re.sub(r",\s*,+", ",", s)
    s = re.sub(r"\(\s+", "(", s)
    s = re.sub(r"\s+\)", ")", s)
    # Comma splice left behind when a heading was stripped: "Topic, is a ..."
    s = re.sub(r"(?<=[A-Za-z])\s*,\s+(?=(?:is|are|was|were|means|refers|describes|occurs|consists|involves)\b)", " ", s)
    # Double subject-verb from stitched chunks: "the the", "is is"
    s = re.sub(r"\b(\w+)\s+\1\b", r"\1", s, flags=re.I)
    s = re.sub(r"^[,;:.\-\s]+", "", s)
    if s and s[0].islower() and not re.match(r"^(?:e\.g|i\.e|vs|etc)\b", s):
        s = s[0].upper() + s[1:]
    return s


PLACEHOLDER = "\x00RX{}Z\x00"


def _protect(text: str) -> Tuple[str, Dict[str, str]]:
    """Hide code blocks, inline code and links so grammar/honorific passes
    never corrupt URLs, code or markdown link targets."""
    store: Dict[str, str] = {}

    def hide(m: re.Match) -> str:
        key = PLACEHOLDER.format(len(store))
        store[key] = m.group(0)
        return key

    text = re.sub(r":::urdu[\s\S]*?:::", hide, text)
    text = re.sub(r"```[\s\S]*?```", hide, text)
    text = re.sub(r"`[^`\n]+`", hide, text)
    text = re.sub(r"\[[^\]]+\]\([^)\s]+\)", hide, text)
    text = re.sub(r"https?://[^\s)\]]+", hide, text)
    return text, store


def _restore(text: str, store: Dict[str, str]) -> str:
    for key, value in store.items():
        text = text.replace(key, value)
    return text


def polish_text(text: str) -> str:
    """Grammar pass + remove any heading that appears more than once."""
    protected, store = _protect(text or "")
    out: List[str] = []
    seen_headings = set()
    for line in protected.split("\n"):
        stripped = line.strip()
        if not stripped:
            out.append("")
            continue
        if "\x00" in line:                     # protected content (link/code/url)
            out.append(line)
            continue
        hm = re.match(r"^(#{1,6})\s+(.+?)\s*$", line)
        if hm:
            key = re.sub(r"[^a-z0-9]+", " ", hm.group(2).lower()).strip()
            if key in seen_headings:
                continue                       # <- kills repeated headings
            seen_headings.add(key)
            out.append(f"{hm.group(1)} {clean_sentence(hm.group(2))}")
            continue
        if line.lstrip().startswith("|"):      # markdown table
            out.append(line)
            continue
        bm = re.match(r"^(\s*(?:[-*]|\d+\.)\s+)(.*)$", line)
        if bm:
            out.append(bm.group(1) + clean_sentence(bm.group(2)))
            continue
        qm = re.match(r"^(\s*>\s*)(.*)$", line)
        if qm:
            out.append(qm.group(1) + clean_sentence(qm.group(2)))
            continue
        out.append(clean_sentence(line))
    cleaned = "\n".join(out)
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned).strip()
    return _restore(cleaned, store) + "\n"


# ---------------------------------------------------------------------------
# Respect / etiquette layer
# ---------------------------------------------------------------------------

RELIGION_RE = re.compile(
    r"\b(prophet|prophets|prophethood|messenger|apostle|religion|religions|religious|"
    r"islam|islamic|muslim|muslims|quran|qur'an|koran|hadith|sunnah|allah|mosque|masjid|"
    r"hajj|umrah|ramadan|eid|halal|haram|fatwa|sharia|shari'ah|sunni|shia|shi'a|sufi|imam|caliph|"
    r"bible|torah|gospel|scripture|scriptures|christian|christianity|church|jesus|christ|"
    r"judaism|jewish|jew|jews|synagogue|rabbi|hindu|hinduism|veda|vedas|bhagavad|krishna|"
    r"buddha|buddhism|sikh|sikhism|guru nanak|gurdwara|zoroaster|confucius|taoism|"
    r"muhammad|mohammad|mohammed|ibrahim|abraham|musa|moses|isa|noah|nuh|adam|"
    r"yusuf|joseph|dawud|david|sulayman|solomon|maryam|mary|pbuh|"
    r"god|deity|worship|pray|prayer|salah|salat|faith|believers|belief|heaven|hell|"
    r"angel|angels|revelation|miracle|fasting|pilgrimage|mosques|churches|temples)\b",
    re.IGNORECASE,
)

# Never attach a prophetic honorific to a modern person's name, e.g. the poet
# "Allama Muhammad Iqbal" or the boxer "Muhammad Ali": a following capitalised
# surname means this is not the Prophet.
MUHAMMAD_RE = re.compile(
    r"(?i:\b(Muhammad|Mohammad|Mohammed|Mahomet|Prophet Muhammad)\b)"
    r"(?!\s*(?i:ﷺ|\(peace be upon him\)|PBUH|,\s*peace))"
    r"(?!\s+[A-Z][a-z]{2,})"
)

OTHER_PROPHETS = [
    "Ibrahim", "Abraham", "Musa", "Moses", "Isa", "Jesus", "Nuh", "Noah",
    "Adam", "Yusuf", "Joseph", "Dawud", "David", "Sulayman", "Solomon",
    "Ishaq", "Isaac", "Ismail", "Ishmael", "Yaqub", "Jacob", "Harun", "Aaron",
    "Yahya", "Zakariya", "Zechariah", "Ilyas", "Elijah", "Ayyub", "Job",
    "Yunus", "Jonah", "Lut", "Lot", "Idris", "Hud", "Salih", "Shu'ayb",
]


def is_religious(text: str) -> Tuple[bool, List[str]]:
    """Return (is_religious_topic, matched terms)."""
    text = text or ""
    found = list(dict.fromkeys(m.group(0).lower() for m in RELIGION_RE.finditer(text)))
    # "Allama Muhammad Iqbal" is a poet, not a reference to the Prophet.
    if re.search(r"\bMuhammad\s+[A-Z][a-z]{2,}", text):
        found = [f for f in found if f != "muhammad"]
    return bool(found), found[:8]


def apply_honorifics(text: str, respect_mode: str, style: str) -> str:
    """Insert prophetic honorifics without touching URLs, code or link targets."""
    protected, store = _protect(text or "")
    muh_suffix = " ﷺ" if style == "arabic" else " (peace be upon him)"
    protected = MUHAMMAD_RE.sub(lambda m: m.group(0) + muh_suffix, protected)
    if respect_mode == "islamic":
        for name in OTHER_PROPHETS:
            pat = re.compile(r"\b(" + re.escape(name) + r")\b(?!\s*(?:ﷺ|\(peace be upon him\)|PBUH))")
            protected = pat.sub(lambda m: m.group(0) + " (peace be upon him)", protected)
    return _restore(protected, store)


def respect_note(question: str, opts: Dict[str, Any]) -> str:
    _, matched = is_religious(question)
    topics = ", ".join("`" + m + "`" for m in matched[:5]) if matched else "religious subjects"
    mode = opts.get("respect_mode", "balanced")
    lines = [
        "This question touches on " + topics + ". I handle prophets, Scriptures, religions and "
        "believers with courtesy and care. My commitments here:",
        "",
        "- I use respectful language for every prophet, Scripture and faith, and I never joke about, "
        "mock or caricature them.",
        "- I describe traditions **neutrally**: I do not rank religions, declare any community right "
        "or wrong, or take sides in sectarian disagreements. Where views differ, I attribute them "
        "(for example, \"in Islamic tradition...\", \"Christian sources state...\").",
        "- I am an AI research assistant, **not a scholar or a religious authority**. I do not issue "
        "fatwas, legal rulings or personal religious guidance. For rulings and practice, please "
        "consult qualified scholars and your own Scripture and community.",
        "- I do not invent details about a prophet's life or a tradition's teachings. Anything I "
        "cannot verify from the sources below is clearly marked as unverified.",
    ]
    if mode == "islamic" and opts.get("honorifics", "none") != "none":
        suffix = "ﷺ" if opts.get("honorifics") == "arabic" else "(peace be upon him)"
        lines.append(f"- As requested in Settings, prophets are mentioned with the honorific **{suffix}** "
                     "wherever they appear in this answer.")
    return "## A note on respect\n\n" + "\n".join(lines)


# ---------------------------------------------------------------------------
# Settings
# ---------------------------------------------------------------------------

DEFAULT_OPTS: Dict[str, Any] = {
    "respect": True,
    "respect_mode": "balanced",       # balanced | islamic | off
    "honorifics": "arabic",           # arabic | english | none
    "grammar": True,
    "style": "structured",            # structured | simple | academic | exam
    "breadth": 2,                    # Wikipedia articles read per question (1-4)
    "simple_english": False,
    "english_level": "intermediate",  # simple | intermediate | detailed
    "auto_learn": True,
    "sections": {
        "overview": True, "history": True, "mechanism": True, "types": True,
        "applications": True, "limitations": True, "comparison": True,
        "faq": True, "glossary": True, "timeline": True,
    },
}


def default_opts(opts: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    o = dict(DEFAULT_OPTS)
    o["sections"] = dict(DEFAULT_OPTS["sections"])
    for k, v in (opts or {}).items():
        if k == "sections" and isinstance(v, dict):
            o["sections"].update({sk: bool(sv) for sk, sv in v.items() if sk in DEFAULT_OPTS["sections"]})
        elif k in o:
            o[k] = v
    if o["respect_mode"] not in ("balanced", "islamic", "off"):
        o["respect_mode"] = "balanced"
    if o["honorifics"] not in ("arabic", "english", "none"):
        o["honorifics"] = "arabic"
    if o["style"] not in ("structured", "simple", "academic", "exam"):
        o["style"] = "structured"
    if o.get("english_level") not in ("simple", "intermediate", "detailed"):
        o["english_level"] = "intermediate"
    try:
        o["breadth"] = max(1, min(4, int(o["breadth"])))
    except (TypeError, ValueError):
        o["breadth"] = 2
    for flag in ("respect", "grammar", "simple_english", "auto_learn"):
        o[flag] = bool(o[flag])
    return o


def respect_on(opts: Optional[Dict[str, Any]] = None) -> bool:
    o = default_opts(opts)
    return bool(o["respect"]) and o["respect_mode"] != "off"


# ---------------------------------------------------------------------------
# Composer helpers
# ---------------------------------------------------------------------------


def best_lead(question: str, leads: List[str]) -> str:
    q = set(tokens(question))
    causal = bool(re.match(r"^\s*why\b", (question or "").lower()))
    best_text, best_score = "", -1.0
    for i, lead in enumerate(leads or []):
        sents = [clean_sentence(s) for s in sentences(clean_wiki(lead)) if 25 <= len(s) <= 340]
        if not sents:
            continue
        score = 3.0 * len(q & set(tokens(sents[0])))
        score += sum(len(q & set(tokens(s))) for s in sents[1:4])
        score += 5.0 * (len(leads) - i)
        if re.search(r"\b(is|are|refers to|caused by|due to|occurs|describes)\b", sents[0].lower()):
            score += 2.0
        if causal and re.search(r"scatter|because|due to|caused by|wavelength|absorb|reflect|radiation", lead.lower()):
            score += 5.0
        if score > best_score:
            best_score, best_text = score, " ".join(sents[:2])
    return clean_sentence(best_text[:800])


def best_summary(question: str, hits: List[Dict[str, Any]]) -> str:
    q = set(tokens(question))
    cands: List[Tuple[float, str]] = []
    for rank, h in enumerate((hits or [])[:12]):
        for raw in sentences(clean_wiki(h.get("text", ""))):
            s = clean_sentence(raw)
            if len(s) < 55 or len(s) > 330:
                continue
            score = 2.0 * len(q & set(tokens(s))) + 3.0 / (1 + rank)
            if re.search(r"\b(is|are|was|were|refers to|means|defined as|known as|occurs|caused by)\b", s.lower()):
                score += 2.5
            cands.append((score, s))
    if not cands:
        return clean_sentence(clean_wiki(hits[0].get("text", ""))[:400]) if hits else ""
    cands.sort(key=lambda x: -x[0])
    chosen, seen = [], set()
    for _, s in cands:
        key = s[:55].lower()
        if key in seen:
            continue
        seen.add(key)
        chosen.append(s.rstrip(".") + ".")
        if len(chosen) >= 2:
            break
    return clean_sentence(" ".join(chosen)[:800])


def key_points(question: str, hits: List[Dict[str, Any]], n: int = 6) -> List[str]:
    q = set(tokens(question))
    cands: List[Tuple[int, str]] = []
    for h in hits or []:
        for raw in sentences(clean_wiki(h.get("text", ""))):
            s = clean_sentence(raw)
            if len(s) < 45 or len(s) > 260:
                continue
            cands.append((len(q & set(tokens(s))) + min(len(s) // 120, 1), s))
    cands.sort(key=lambda x: -x[0])
    out, seen = [], set()
    for _, s in cands:
        k = s[:60].lower()
        if k in seen:
            continue
        seen.add(k)
        out.append(s.rstrip(".") + ".")
        if len(out) >= n:
            break
    return out or ["The retrieved sources agree on the core definition but differ in scope and emphasis."]


def group_passages(hits: List[Dict[str, Any]], cap: int,
                   per_title: int = 3) -> Dict[str, List[str]]:
    """Group by source title so the same '### Title' heading never repeats."""
    groups: Dict[str, List[str]] = {}
    total = 0
    for h in hits or []:
        title = h.get("title") or "Source"
        text = clean_wiki(h.get("text", ""))
        if len(text) < 40:
            continue
        if title not in groups:
            groups[title] = []
        if len(groups[title]) >= per_title:
            continue
        if any(text[:80] == prev[:80] for prev in groups[title]):
            continue
        groups[title].append(text[:1200])
        total += 1
        if total >= cap:
            break
    return groups


def all_sentences(hits: List[Dict[str, Any]]) -> List[str]:
    out = []
    for h in hits or []:
        for raw in sentences(clean_wiki(h.get("text", ""))):
            s = clean_sentence(raw)
            if 45 <= len(s) <= 280:
                out.append(s)
    return list(dict.fromkeys(out))


def take_sentences(pool: List[str], pattern: str, n: int,
                   exclude: Optional[set] = None, style: str = "structured") -> List[str]:
    rx = re.compile(pattern, re.IGNORECASE)
    exclude = exclude or set()
    picked = []
    for s in pool:
        key = s[:60].lower()
        if key in exclude or not rx.search(s):
            continue
        if style == "simple" and len(s) > 190:
            continue
        exclude.add(key)
        picked.append(s.rstrip(".") + ".")
        if len(picked) >= n:
            break
    return picked


def topic_title(hits: List[Dict[str, Any]], question: str) -> str:
    if hits:
        t = hits[0].get("title") or ""
        if t:
            return t.split("(")[0].strip()
    words = [w for w in re.findall(r"[A-Za-z][A-Za-z'-]+", question or "") if w.lower() not in STOPWORDS]
    return " ".join(words[:4]) or "this topic"


GLOSSARY_STOP = set("""about above across after again against along among around because before
being below between both called contain contains could different during each early enough every
example examples first general however including into itself later likely little machine many
might more most much often other over rather really result results same several should since
some such than that their them these thing things this those three through toward towards
under until upon usually very well were where which while whose within without would your
firstly secondly thirdly finally therefore moreover however although together across
process processes system systems level levels number numbers period periods
known named given shown shows include includes including called termed
time times year years part parts case cases way ways form forms type types""".split())


def build_glossary(hits: List[Dict[str, Any]], n: int = 6) -> List[Tuple[str, str]]:
    """Fallback glossary: one concept per source title, never random tokens."""
    out, seen = [], set()
    for h in hits or []:
        title = (h.get("title") or "").split("(")[0].strip()
        if not title or title.lower() in seen:
            continue
        seen.add(title.lower())
        passages = [clean_wiki(x.get("text", "")) for x in hits
                    if x.get("title") == h.get("title")]
        lines = [clean_sentence(s) for p in passages
                 for s in sentences(p) if 55 <= len(s) <= 280]
        key = set(tokens(title))
        best = ""
        for s in lines:
            if len(key & set(tokens(s[:100]))) >= 1 and re.search(
                    r"\b(?:is|are|was|were|means|refers|describes)\b", s[:140], re.I):
                best = s
                break
        if not best and lines:
            best = lines[0]
        if best:
            out.append((title, best))
        if len(out) >= n:
            break
    return out


DATE_RE = re.compile(r"\b(1[0-9]{3}|20[0-2][0-9])\b")
MECHANISM_RE = r"\b(because|due to|mechanism|process|occurs|results in|causes|produces|converts|consists of|involves|allows|enables|depends on|by means of|through the)\b"
TYPE_RE = r"\b(types?|kinds?|classes|categories|classified|divided into|two main|three main|varieties|forms of|is a type of|subset|variants?)\b"
APPLICATION_RE = r"\b(used in|used for|applied|application|applications|commonly|widely|industry|industries|in practice|real-world|everyday|deployed|employed|utilised|utilized)\b"
LIMIT_RE = r"\b(however|although|limitation|limited|cannot|difficult|challenge|drawback|disadvantage|risk|misconception|debated|disputed|uncertain|critici)\w*\b"
HISTORY_RE = r"\b(history|historical|first|origin|originally|developed|discovered|invented|ancient|century|founded|began|early|tradition|since|in \d{4})\b"


def build_timeline(pool: List[str], n: int = 5) -> List[Tuple[str, str]]:
    out, seen = [], set()
    for s in pool:
        m = DATE_RE.search(s)
        if not m or s[:60].lower() in seen:
            continue
        seen.add(s[:60].lower())
        out.append((m.group(1), s))
        if len(out) >= n:
            break
    return out


def build_faq(question: str, hits: List[Dict[str, Any]], n: int = 3) -> List[Tuple[str, str]]:
    topic = topic_title(hits, question)
    pool = all_sentences(hits)
    qset = set(tokens(question))
    prompts = [
        (f"What exactly is {topic}?", r"\b(is|are|refers to|means|defined as)\b"),
        (f"How does {topic} work?", MECHANISM_RE),
        (f"Why does {topic} matter, and where is it used?", APPLICATION_RE),
        (f"What are the limits or open questions about {topic}?", LIMIT_RE),
    ]
    out, used = [], set()
    for q, pattern in prompts:
        rx = re.compile(pattern, re.I)
        best, best_score = "", -1.0
        for s in pool:
            k = s[:60].lower()
            if k in used:
                continue
            score = len(qset & set(tokens(s))) + (3 if rx.search(s) else 0)
            if score > best_score:
                best, best_score = s, score
        if best:
            used.add(best[:60].lower())
            out.append((q, best.rstrip(".") + "."))
        if len(out) >= n:
            break
    return out


class Builder:
    """Collect sections and guarantee each heading appears exactly ONCE."""

    def __init__(self) -> None:
        self.parts: List[str] = []
        self.seen: set = set()

    def add(self, heading: str, body: str, level: int = 2) -> None:
        body = (body or "").strip()
        if not body:
            return
        key = re.sub(r"[^a-z0-9]+", " ", heading.lower()).strip()
        if key in self.seen:
            return
        self.seen.add(key)
        self.parts.append("#" * level + " " + heading + "\n\n" + body + "\n")

    def render(self) -> str:
        return "\n".join(self.parts).strip() + "\n"


def compose_answer(question: str, hits: List[Dict[str, Any]],
                   leads: Optional[List[str]] = None,
                   sources: Optional[List[Dict[str, str]]] = None,
                   depth: str = "deep",
                   opts: Optional[Dict[str, Any]] = None,
                   kb_count: int = 0, chunks: int = 0,
                   index_titles: Optional[List[str]] = None,
                   terms: Optional[List[Tuple[str, str]]] = None) -> str:
    """Build a structured, sourced answer with no repeated headings.

    Depth is a real contract, not a cosmetic label:
      quick       short answer + 3 key points + sources + next step   (~600-1200 chars)
      standard    + 4 passages of detail + a short example            (~2500-4000)
      deep        + overview + 8 passages + worked angle + limits      (~5000-7000)
      exhaustive  + mechanism, types, history, timeline, uses,
                    comparison, FAQ, glossary, honest gaps             (~9000+)
    """
    o = default_opts(opts)
    sec = o["sections"]
    style = o["style"]
    sources = sources or []
    hits = hits or []
    if not hits:
        return ""

    is_quick = depth == "quick"
    is_std = depth == "standard"
    is_deep = depth == "deep"
    is_ex = depth == "exhaustive"
    long = is_deep or is_ex

    cap = {"quick": 2, "standard": 4, "deep": 8, "exhaustive": 20}.get(depth, 8)
    groups = group_passages(hits, cap, per_title=8 if is_ex else 3)
    pool = all_sentences(hits)
    short = best_lead(question, leads or []) or best_summary(question, hits)
    short_keys = {s[:50].lower() for s in sentences(short)}
    used: set = set(s[:60].lower() for s in sentences(short or ""))
    b = Builder()

    if short:
        if style == "simple" or is_quick:
            short = "**In simple terms:** " + short
        elif style == "academic":
            short += ("\n\n*Scope note:* the summary below follows the retrieved encyclopaedic "
                      "sources; terminology and periodisation may differ between scholarly traditions.")
        b.add("Short answer", short)

    if long and sec.get("overview"):
        cand = [s for s in pool
                if s[:50].lower() not in short_keys and 70 <= len(s) <= 300]
        overview = clean_sentence(" ".join(cand[:2])[:520])
        if overview:
            b.add("Overview and definition",
                  overview + "\n\nThe sections below unpack the definition, the mechanism, the "
                  "history, the practical uses and the limits, using only the sources listed at the end.")

    # --- In detail: one heading per source, never repeated -----------------
    # Quick answers skip this section entirely; standard/deep/exhaustive get
    # progressively more grouped passages.
    if not is_quick:
        detail_parts: List[str] = []
        titles: List[str] = []
        for title, passages in groups.items():
            titles.append(title)
            body = "\n\n".join(passages)
            if is_std:
                body = body[:900]
            detail_parts.append("### " + clean_sentence(title) + "\n\n" + body)
        if detail_parts:
            b.add("In detail", "\n\n".join(detail_parts))
    else:
        titles = list(groups.keys())

    if is_ex:
        if sec.get("mechanism"):
            items = take_sentences(pool, MECHANISM_RE, 5, used, style)
            body = "\n".join(f"- {s}" for s in items) if items else (
                "The retrieved passages describe the subject but do not spell out a step-by-step "
                "mechanism. I am not going to invent one; the closest sourced statements are in "
                "**In detail** above.")
            b.add("How it works, step by step", body)

        if sec.get("types"):
            items = take_sentences(pool, TYPE_RE, 4, used, style)
            body = "\n".join(f"- {s}" for s in items) if items else (
                "The sources consulted do not give an explicit classification or list of types for "
                "this topic. That is a genuine gap in the retrieved material, not an omission on "
                "my part.")
            b.add("Types and classifications", body)

        if sec.get("history"):
            items = take_sentences(pool, HISTORY_RE, 5, used, style)
            body = "\n".join(f"- {s}" for s in items) if items else (
                "No dated historical account appeared in the retrieved passages. For a reliable "
                "history you would need a primary chronology or a specialist source.")
            b.add("Background and history", body)

        if sec.get("timeline"):
            rows = build_timeline(pool, 5)
            body = "\n".join(f"- **{year}** - {s.rstrip('.')}." for year, s in rows) if rows else (
                "No verifiable dated milestones appear in the retrieved text, so I am not "
                "supplying a timeline rather than guessing dates.")
            b.add("Timeline of dated milestones", body)

        if sec.get("applications"):
            items = take_sentences(pool, APPLICATION_RE, 5, used, style)
            body = "\n".join(f"- {s}" for s in items) if items else (
                "The retrieved sources focus on the definition and theory rather than practical "
                "applications; I will not manufacture examples.")
            b.add("Applications and real-world use", body)

    # --- Key points ---------------------------------------------------------
    want = 3 if is_quick else (4 if is_std else 6)
    kp = [p for p in key_points(question, hits, want + 8)
          if p[:50].lower() not in short_keys][:want]
    if not kp:
        kp = [s.rstrip(".") + "." for s in pool[:want]] or [
            "The retrieved sources agree on the core definition but differ in scope and emphasis."]
    b.add("Key points", "\n".join(f"- {clean_sentence(p)}" for p in dict.fromkeys(kp)))

    if is_std:
        b.add("Practical angle",
              "Start from the definition above, change one variable at a time, and check the "
              "result against a second source. Tell me your actual goal - an exam answer, a "
              "project decision or code - and I will rewrite this around it.")

    if long:
        lead = clean_sentence(pool[0]) if pool else short
        b.add("Example and practical angle",
              f"To make \"{' '.join((question or '').split())[:110]}\" concrete, start from the "
              f"definition and change one variable at a time. {lead}\n\n"
              "A reliable pattern: (1) name the thing precisely, (2) identify the mechanism, "
              "(3) plug in a small example you can check by hand, (4) compare with a second "
              "source, (5) note where the rule stops applying. Tell me your actual goal - an "
              "exam answer, a project decision or code - and I will rewrite this around it.")

    if is_ex and sec.get("limitations"):
        items = take_sentences(pool, LIMIT_RE, 4, used, style)
        body = "\n".join(f"- {s}" for s in items) if items else ""
        body += ("\n\n- Treat a summary as the whole topic: the passages above are excerpts, not "
                 "the full source.\n- Assume a general explanation covers your specific case; "
                 "context (date, version, units) changes answers.\n- Confuse correlation or "
                 "analogy with causation.\n- Trust a single source for anything consequential.")
        b.add("Advantages, limitations and common mistakes", body.lstrip())
    elif is_deep:
        b.add("Common mistakes and limits",
              "- Treating a summary as the whole topic: the passages above are excerpts, not the full source.\n"
              "- Assuming a general explanation covers your specific case; context changes answers.\n"
              "- Confusing correlation or analogy with causation.\n"
              "- Trusting a single source. Cross-check anything used for a decision.")

    if is_ex and sec.get("comparison"):
        rows = []
        for title in titles[1:5]:
            sentence = next((s for s in pool if tokens(title) and len(set(tokens(title)) & set(tokens(s))) >= 1), "")
            rows.append(f"- **{title}** - {sentence.rstrip('.') + '.' if sentence else 'a related source in the reading list below.'}")
        if not rows:
            rows = ["- The retrieved material did not include a directly comparable topic; "
                    "ask me to compare it with a specific alternative and I will research both."]
        b.add("Comparison with related ideas", "\n".join(rows))

    if is_ex and sec.get("faq"):
        rows = []
        for q, a in build_faq(question, hits, 3):
            rows.append(f"**{q}**\n\n{clean_sentence(a)}")
        if rows:
            b.add("Frequently asked questions", "\n\n".join(rows))

    if is_ex and sec.get("glossary"):
        rows = []
        if terms:
            for heading, text in terms[:8]:
                parts = sentences(clean_wiki(text))
                if parts:
                    rows.append("- **" + clean_sentence(heading) + "** - " +
                                clean_sentence(parts[0])[:260])
        else:
            rows = [f"- **{term}** - {clean_sentence(s)}"
                    for term, s in build_glossary(hits, 6)]
        if rows:
            b.add("Glossary of key terms", "\n".join(rows))

    if style == "exam" and long:
        b.add("Exam-ready summary",
              clean_sentence(short) + "\n\n" +
              "\n".join(f"- {clean_sentence(p)}" for p in kp[:4]) +
              "\n\n*Tip:* state the definition first, then the mechanism, then one example, "
              "then one limitation. That structure covers most marking schemes.")
    elif style == "academic" and is_ex:
        b.add("Scope, sources and terminology",
              "This answer is a synthesis of encyclopaedic and curated summaries, not a primary "
              "research review. Terminology, periodisation and emphasis can differ across "
              "traditions and disciplines; consult the sources below for primary claims.")

    # --- Sources (deduplicated) --------------------------------------------
    src_lines, seen_urls, seen_titles = [], set(), set()
    for src in sources:
        url = src.get("url", "")
        title = src.get("title", "")
        if url and url not in seen_urls:
            seen_urls.add(url)
            src_lines.append(f"- [{title}]({url}) - {src.get('kind','source')}")
        elif not url and title and title not in seen_titles:
            seen_titles.add(title)
            src_lines.append(f"- Curated knowledge: {title}")
    for t in titles:
        if t not in seen_titles:
            seen_titles.add(t)
            src_lines.append(f"- Curated passage: {t}")
    if not src_lines:
        src_lines.append(f"- Curated knowledge base (`knowledge_base.json`), {kb_count} topics / {chunks} indexed chunks.")
    b.add("Sources", "\n".join(dict.fromkeys(src_lines)))

    if not is_quick:
        b.add("What I could not verify",
              "The passages above come from a curated base and Wikipedia extracts. They may omit very "
              "recent events, primary research, specialised data or niche specifics. If your question "
              "depends on a date, a number, a named source or a religious ruling, tell me which and I "
              "will mark it explicitly rather than guessing.")

    b.add("Keep going",
          "Ask a narrower follow-up, request a Python snippet or a comparison table, or type "
          f"`/learn {topic_title(hits, question)[:40]}` to cache the full source article for "
          "offline use. I never stop at a shrug - there is always a next useful step."
          if not is_quick else
          "Choose **standard**, **deep** or **exhaustive** above for the full multi-section "
          "explanation, or ask a narrower follow-up. I never stop at a shrug.")

    return b.render()


def condense(text: str, n: int = 2, limit: int = 700) -> str:
    real = [clean_sentence(s) for s in sentences(clean_wiki(text)) if len(s) > 40]
    return " ".join(real[:n])[:limit]


def finalize_answer(answer: str, question: str,
                    opts: Optional[Dict[str, Any]] = None) -> str:
    """THE single choke point: respect note, grammar, honorifics, heading dedupe.

    Called by Ryzek._finish() for quick replies, researched answers, LLM
    output and the honest fallback alike.
    """
    o = default_opts(opts)
    out = answer or ""
    if respect_on(o) and is_religious(question)[0]:
        out = respect_note(question, o) + "\n\n" + out
    if o["grammar"]:
        out = polish_text(out)
    if respect_on(o) and o["honorifics"] != "none" and is_religious(question)[0]:
        out = apply_honorifics(out, o["respect_mode"], o["honorifics"])
    return out.strip() + "\n"
