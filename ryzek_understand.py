#!/usr/bin/env python3
"""
Ryzek AI v2.6 - the understanding layer.

The complaint that started this file: the old engine matched keywords, so
"what is the difference between affect and effect" retrieved passages about the
greenhouse effect, and "why does my phone battery drain fast" produced a generic
framework instead of an answer.

This module looks at the question BEFORE any retrieval happens and answers four
questions:

    intent   what kind of thing is being asked (definition, how-to, cause,
             comparison, list, opinion, personal, writing, follow-up, ...)
    entities the actual subject - not the instruction words
             ("type essay on climate change" -> "climate change")
    shape    what a good answer to this intent looks like (lead sentence +
             sections), so the composer can be steered per intent
    plan     human-readable reading plan shown in the UI, e.g.
             "Intent: cause  ->  Subject: phone battery drain  ->  Live check"

Everything here is deterministic and testable - no model weights, no network.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

# ---------------------------------------------------------------------------
# vocabulary
# ---------------------------------------------------------------------------

STOP = set("""
a an the and or of to in on for with is are was were be been being it its this that these those
as at by from into about over under than then so if but not no do does did doing have has had
having i you he she they we me my your our their them him her who whom what which when where why
how can could should would will shall may might must please tell explain define describe give show
make want need answer question me my mine ours yours also just really very quite some any more
most much many few lot lots thing things stuff kind sort way ways actually basically honestly
""".split())

# Words that describe the request rather than the subject.
INSTRUCTION = set("""
write type draft compose create generate produce make me please essay article speech report
letter email e mail paragraph summary paragraph short long brief detailed full simple easy
quick explain describe define tell show give list outline mention discuss compare contrast
between difference differences versus vs same different better best worse worst
and or but also plus
translate rewrite improve fix correct check proofread summarize summarise expand shorten
continue elaborate clarify rephrase paraphrase
""".split())

# Topic words that make a question about Ryzek itself.
SELF_WORDS = set("""you your yourself ryzek name identity ai bot assistant creator maker
owner boss developer who whom what""".split())

PERSONAL_WORDS = set("""remember recall forgot forget remembered memory remember me
my name my favourite my favorite am i was i i'm i am did i earlier before previously
last time yesterday told said asked""".split())

WRITING_WORDS = set("""write type draft compose generate essay article speech report letter
email paragraph story poem poetry ghazal nazm shayari song caption bio application complaint
invitation notice memo review""".split())

HOWTO_WORDS = set("""how steps step guide way ways tip tips improve become learn fix solve
setup set up install change make better faster cheaper safer""".split())

CAUSE_WORDS = set("""why cause causes caused reason reasons behind happen happens happening""".split())

COMPARE_WORDS = set("""compare comparison difference differences versus vs better best worse
pros cons advantage advantages disadvantage disadvantages""".split())

OPINION_WORDS = set("""should i is it worth recommend advice advise opinion think suggest
suggestion idea ideas choose pick""".split())

LIST_WORDS = set("""list examples example types kinds list names top best famous main major
different""".split())

DEFINITION_START = re.compile(
    r"^(what|who)\s+(is|are|was|were|does|do|did)\s+(the\s+|a\s+|an\s+)?", re.I)

# "explain X to a 10 year old", "in simple words", "like I'm five"
AUDIENCE_RE = re.compile(
    r"\b(to|for)\s+(a\s+|an\s+)?(?:\d{1,2}[\s-]?year[\s-]?old|kid|child|beginner|"
    r"student|teenager|grandma|expert|professional|developer|business\s+owner)\b", re.I)
SIMPLE_RE = re.compile(
    r"\b(simple words|simply|simplest|easy words|layman|eli5|explain like|"
    r"for dummies|in short|briefly|quickly)\b", re.I)
LENGTH_RE = re.compile(
    r"\b(in\s+)?(\d+|one|two|three|four|five|ten)\s+(lines?|paragraphs?|sentences?|"
    r"bullet points?|words?)\b", re.I)

# Filler phrases to strip before looking for the subject.
LEAD_FILLER = [
    r"^(hey|hi|hello|yo|ok|okay|so|well|um|uh|please|pls|plz|bro|dude|sir|madam|boss)\b[,!. ]*",
    r"^(can|could|would|will)\s+you\s+(please\s+)?",
    r"^(i\s+want\s+(to\s+know|you\s+to)|i\s+need\s+(to\s+know|you\s+to)|i'd\s+like\s+(to\s+know|you\s+to))\s+",
    r"^(do\s+you\s+know|do\s+you\s+think|tell\s+me|explain\s+to\s+me|let\s+me\s+know)\s+(about\s+)?",
    r"^(what|who)\s+(is|are|was|were)\s+(the\s+|a\s+|an\s+)?",
    r"^(how\s+(do|does|did|can|could|should|would)\s+(i|we|you|one))\s+",
    r"^(how\s+(do|does|did|can|could|should|would|to))\s+",
    r"^(why\s+(is|are|do|does|did|was|were))\s+",
    r"^(define|describe|explain|discuss|summarise|summarize|outline)\s+",
    r"^(whats|what's)\s+the\s+(best|easiest|fastest|right|correct)\s+(way|method|approach)\s+(to)?\s*",
    r"^(what|which)\s+is\s+the\s+(best|easiest|fastest|right|correct)\s+(way|method)\s+(to)?\s*",
    r"^(how\s+(do|can|should|would)\s+(i|we|you))\s+",
    r"^(how\s+to)\s+",
    r"^(i\s+(want|wanna|need|would\s+like)\s+to)\s+",
    r"^(get|become|be)\s+(better|good)\s+at\s+",
    r"^(get|become|be)\s+good\s+at\s+",
    r"^(what|where)\s+should\s+(i|we)\s+",
    r"^(the\s+)?(definition|meaning|concept|idea)\s+(of|behind)\s+",
]

BENGALI_URDU_HINT = re.compile(r"[\u0600-\u06FF\u0750-\u077F]")


# ---------------------------------------------------------------------------
# result object
# ---------------------------------------------------------------------------

@dataclass
class Understanding:
    original: str
    clean: str = ""
    intent: str = "definition"          # definition|howto|cause|comparison|list|opinion
                                        # |personal|identity|smalltalk|writing|math|followup|general
    subject: str = ""                   # the entity we should research
    subject_terms: List[str] = field(default_factory=list)
    keywords: List[str] = field(default_factory=list)
    entities: List[str] = field(default_factory=list)
    wants: List[str] = field(default_factory=list)   # examples, steps, sources, numbers...
    audience: str = ""                  # "simple" | "10-year-old" | "expert"
    language: str = "en"
    is_followup: bool = False
    is_wide: bool = False               # "everything about X" style request
    plan: List[str] = field(default_factory=list)

    def as_dict(self) -> Dict[str, Any]:
        return {"intent": self.intent, "subject": self.subject,
                "keywords": self.keywords[:8], "audience": self.audience,
                "followup": self.is_followup, "wide": self.is_wide,
                "plan": self.plan, "language": self.language}

    def describe(self) -> str:
        """One short line for the UI under the user's message."""
        bits = []
        if self.subject:
            bits.append(self.subject)
        bits.append(_INTENT_LABEL.get(self.intent, self.intent))
        if self.audience == "simple":
            bits.append("simple words")
        elif self.audience:
            bits.append("for " + self.audience)
        if self.is_followup:
            bits.append("using earlier messages")
        return " · ".join(bits)


_INTENT_LABEL = {
    "definition": "definition", "howto": "how-to", "cause": "explains a cause",
    "comparison": "comparison", "list": "list", "opinion": "advice",
    "personal": "memory recall", "identity": "about me", "smalltalk": "small talk",
    "writing": "writing task", "math": "calculation", "followup": "follow-up",
    "general": "general question", "wide": "full overview",
}


# ---------------------------------------------------------------------------
# small helpers
# ---------------------------------------------------------------------------

def words(text: str) -> List[str]:
    return re.findall(r"[a-zA-Z][a-zA-Z0-9'+#.-]*", text)


def content_terms(text: str) -> List[str]:
    out, seen = [], set()
    for w in words(text.lower()):
        w = w.strip(".'-")
        if len(w) <= 2 or w in STOP or w in INSTRUCTION or w in seen:
            continue
        if len(w) > 4 and w.endswith("s") and not w.endswith("ss"):
            stem = w[:-1]
            if stem in seen:
                continue
            seen.add(stem)
            out.append(stem)
        else:
            seen.add(w)
            out.append(w)
    return out


def strip_filler(text: str) -> str:
    out = text.strip()
    for _ in range(5):
        before = out
        for pat in LEAD_FILLER:
            out = re.sub(pat, "", out, flags=re.I).strip()
        if out == before:
            break
    return out


def _title(subject: str) -> str:
    """'phone battery drain' -> 'phone battery drain' (kept lower-case for
    searching, which works better on every engine)."""
    return " ".join(subject.split())[:90]


# ---------------------------------------------------------------------------
# subject extraction
# ---------------------------------------------------------------------------

def extract_subject(text: str) -> str:
    """Pull out what the question is actually about."""
    clean = re.sub(r"\s+", " ", text).strip()
    clean = re.sub(r"[?!.]+$", "", clean)

    # 0) "tell me everything about X" / "all about X" -> X
    m = re.search(r"\b(?:tell\s+me\s+)?(?:everything|all|anything)\s+(?:about|on|regarding)\s+(.+)$",
                  clean, re.I)
    if m:
        inner = m.group(1).strip(" .,-!?")
        if inner:
            return _title(_tidy_subject(inner))

    # 1) explicit "X vs Y" comparisons keep both sides
    m = re.search(r"\b([\w\s'+#-]{2,40}?)\s+(?:vs\.?|versus|or)\s+([\w\s'+#-]{2,40}?)(?:\s|$)",
                  clean, re.I)
    if m and re.search(r"\b(vs\.?|versus|difference|better|compare)\b", clean, re.I):
        a = strip_filler(m.group(1)).strip(" ,")
        b = strip_filler(m.group(2)).strip(" ,")
        if a and b and len(a) < 40 and len(b) < 40:
            return f"{a} vs {b}"

    # 2) "difference between A and B"
    m = re.search(r"difference(?:s)?\s+(?:between\s+)?([\w\s'+#-]{2,40}?)\s+and\s+([\w\s'+#-]{2,40}?)(?:\s|$)",
                  clean, re.I)
    if m:
        a, b = m.group(1).strip(" ,"), m.group(2).strip(" ,")
        if a and b:
            return f"{a} vs {b}"

    # 3) strip lead filler / instruction verbs
    core = strip_filler(clean)
    core = re.sub(r"^(the\s+)(?=\w)", "", core, flags=re.I)

    # 4) keep only the part before a trailing clause
    core = re.split(r"\b(?:for|to|in|with|about|like|because|so that|please|"
                    r"and also|as well)\b", core, maxsplit=1, flags=re.I)[0] or core

    # 5) drop instruction words from the front ("write essay on X" -> "X")
    toks = core.split()
    while toks and toks[0].lower().strip(",.") in INSTRUCTION:
        toks.pop(0)
    while toks and toks[0].lower() in ("about", "on", "of", "the"):
        toks.pop(0)
    core = " ".join(toks)

    # 6) too long? keep the meaningful middle
    if len(core.split()) > 9:
        keep = [w for w in core.split() if w.lower().strip(",.") not in INSTRUCTION]
        core = " ".join(keep) or core

    core = _tidy_subject(core)
    return _title(core.strip(" ,.-") or clean)


_SUBJ_TAIL = ("fast", "quickly", "slowly", "badly", "much", "so", "very", "really",
              "happen", "happens", "work", "works", "do", "does", "mean", "means")


def _tidy_subject(core: str) -> str:
    """'my phone battery drain fast' -> 'phone battery drain'."""
    core = re.sub(r"^(my|our|the|this|that)\s+", "", core.strip(), flags=re.I)
    toks = core.split()
    while toks and toks[-1].lower().strip(",.") in _SUBJ_TAIL:
        toks.pop()
    core = " ".join(toks)
    # "does my phone battery drain" -> "phone battery drain"
    core = re.sub(r"\b(my|our)\s+", "", core, flags=re.I)
    core = re.sub(r"^(i|we|you)\s+", "", core.strip(), flags=re.I)
    core = re.sub(r"\s+", " ", core).strip()
    return core


# ---------------------------------------------------------------------------
# the analyser
# ---------------------------------------------------------------------------

def analyze(text: str, session: Any = None) -> Understanding:
    """Understand a message before answering it."""
    raw = (text or "").strip()
    u = Understanding(original=raw)
    if not raw:
        u.intent = "smalltalk"
        u.plan = ["Empty message"]
        return u

    u.clean = re.sub(r"\s+", " ", raw)
    low = u.clean.lower()
    u.keywords = content_terms(u.clean)

    # --- language hint
    if BENGALI_URDU_HINT.search(raw):
        u.language = "ur"

    # --- audience
    m = AUDIENCE_RE.search(u.clean)
    if SIMPLE_RE.search(u.clean):
        u.audience = "simple"
    elif m:
        phrase = m.group(0)
        if re.search(r"\d{1,2}[\s-]?year[\s-]?old", phrase, re.I):
            u.audience = re.search(r"\d{1,2}", phrase).group(0) + "-year-old"
        else:
            u.audience = re.split(r"\s+", phrase.strip())[-1].replace("-", " ")

    # --- follow-up detection (short message that only makes sense with context)
    if session is not None and getattr(session, "last_topic", None):
        length = len(u.clean.split())
        starts = re.match(r"^(and|also|then|so|why|how|what about|what if|"
                          r"more|tell me more|go on|continue|elaborate|"
                          r"explain that|why so|how so|really|another|"
                          r"example|examples|why not|how come|in urdu|in english|"
                          r"simpler|shorter|longer)\b", low)
        if starts or length <= 3:
            u.is_followup = True

    # --- wide request ("everything about", "all about", "tell me everything")
    if re.search(r"\b(tell\s+me\s+)?(everything|all|anything)\s+(about|on|regarding)\b", low) or \
       re.search(r"\b(complete|full|detailed)\s+(guide|overview|breakdown)\b", low) or \
       re.search(r"\btell me (all|everything)\b", low):
        u.is_wide = True

    # --- intent
    u.intent = _intent(low, u)

    # --- subject
    if u.intent in ("smalltalk", "identity"):
        u.subject = ""
    elif u.intent == "personal":
        u.subject = ""
    else:
        u.subject = extract_subject(u.clean)
        # 'why does my phone battery drain fast' -> 'phone battery drain fast'
        if u.intent == "cause":
            u.subject = re.sub(r"\b(happen|happens|occur|occurs)\b$", "", u.subject).strip()
        u.subject = _tidy_subject(u.subject) if u.subject else u.subject
        if u.is_wide:
            u.subject = re.sub(r"^(tell\s+me\s+)?(everything|all|anything)\s+(about|on|regarding)\s+",
                               "", u.subject, flags=re.I).strip()
            u.subject = re.sub(r"^(about|on|regarding)\s+", "", u.subject, flags=re.I).strip()
            u.intent = "wide"
    u.subject_terms = content_terms(u.subject) if u.subject else []

    # --- what the answer should contain
    if re.search(r"\bexample", low):
        u.wants.append("examples")
    if re.search(r"\bstep|how to|guide|procedure", low):
        u.wants.append("steps")
    if re.search(r"\bsource|cite|citation|reference|link", low):
        u.wants.append("sources")
    if re.search(r"\bnumber|how much|how many|percent|percentage|calculate|total", low):
        u.wants.append("numbers")
    if re.search(r"\bpros and cons|advantage|disadvantage|benefit|drawback", low):
        u.wants.append("pros/cons")
    if re.search(r"\btable|compare|comparison|vs\b", low):
        u.wants.append("comparison")
    if re.search(r"\bhistory|origin|when was", low):
        u.wants.append("history")

    # --- reading plan (shown in the UI)
    plan = []
    if u.is_followup:
        plan.append("Linking this to " + str(getattr(session, "last_topic", "") or "the earlier message")[:60])
    if u.intent == "personal":
        plan.append("Searching your saved memory")
    elif u.subject:
        plan.append(f"Subject: {u.subject[:60]}")
    plan.append("Intent: " + _INTENT_LABEL.get(u.intent, u.intent))
    if u.is_wide:
        plan.append("Building a full topic outline")
    if u.audience:
        plan.append("Tone: " + u.audience)
    if u.wants:
        plan.append("Wants: " + ", ".join(u.wants[:3]))
    u.plan = plan
    return u


def _intent(low: str, u: Understanding) -> str:
    toks = set(re.findall(r"[a-z']+", low))

    if re.fullmatch(r"(hi|hey|hello|yo|hiya|howdy|salam|assalam[ou]?\s*alaikum|"
                    r"good\s+(morning|afternoon|evening|night)|how\s+are\s+you.*|"
                    r"how\s+r\s+u.*|hw\s+r\s+u.*|what'?s\s+up|sup|thanks|thank\s+you|"
                    r"ok|okay|cool|nice|great|bye|goodbye|see\s+you|how\s+do\s+you\s+do|"
                    r"hru|how\s+ru|wassup|hey\s+there|hello\s+there)[!. ]*", low.strip()):
        return "smalltalk"
    if re.search(r"\b(who are you|what are you|your name|who made you|who built you|"
                 r"who created you|who is your (creator|owner|boss|ceo|maker|developer)|"
                 r"what can you do|what do you do|are you (real|human|alive|chatgpt)|"
                 r"which (model|ai) are you|about you|introduce yourself|"
                 r"tell me about yourself|what version)\b", low):
        return "identity"
    asks_about_memory = bool(re.search(
        r"\b(remember|recall|do you know my|do you remember|did i tell you|did i ask|"
        r"what did i|what did we|who am i|what is my|what's my|whats my)\b", low))
    # "what is my name?" is a question; "hi, my name is Ali" is a statement.
    is_question_shape = ("?" in low or asks_about_memory or
                         bool(re.match(r"^(what|who|which|do|did|does|have|has|where|when)\b", low)))
    statement_about_self = bool(re.search(r"\b(my name is|call me)\b", low)) or bool(
        re.search(r"\b(i am|i'm)\s+[A-Z]", getattr(u, "original", "") or ""))
    if asks_about_memory or (statement_about_self and is_question_shape and
                             re.search(r"\bmy\b", low)):
        return "personal"
    if toks & WRITING_WORDS and re.search(
            r"\b(write|type|draft|compose|generate|make|create|likh|likho)\b", low):
        return "writing"
    if re.search(r"[\d]+\s*[\+\-\*/x×]\s*[\d]|(\d+(\.\d+)?\s*%\s*of|percent of)|"
                 r"\b(square root|sqrt|power of|factorial)\b", low):
        return "math"
    if re.search(r"\b(vs\.?|versus|difference between|compared (to|with)|compare)\b", low) \
            and (toks & COMPARE_WORDS or "vs" in low):
        return "comparison"
    if re.search(r"^(why|how come)\b", low) or (toks & CAUSE_WORDS and
                                                re.search(r"\bwhy\b", low)):
        return "cause"
    if re.search(r"^how\b", low) or (toks & HOWTO_WORDS and
                                     re.search(r"\bhow\b", low)):
        return "howto"
    if re.search(r"^(list|name|give me|show me)\b", low) or \
       re.search(r"\b(types of|kinds of|examples of|top \d+)\b", low):
        return "list"
    if toks & OPINION_WORDS and re.search(r"\b(should|worth|recommend|advice|better)\b", low):
        return "opinion"
    if DEFINITION_START.match(low) or re.search(
            r"\b(what is|what are|what does|meaning of|definition of|who is|who was|"
            r"what was|what were|tell me about)\b", low):
        return "definition"
    if u.is_wide:
        return "wide"
    return "general"


# ---------------------------------------------------------------------------
# answer blueprints: what a good answer to each intent looks like
# ---------------------------------------------------------------------------

BLUEPRINTS: Dict[str, Dict[str, Any]] = {
    "definition": {
        "lead": "one clear sentence that says what it is",
        "sections": ["What it is", "How it works", "Why it matters", "Key details",
                     "Common confusion", "Examples"],
    },
    "cause": {
        "lead": "the main cause, stated in one sentence",
        "sections": ["The main cause", "How it happens", "Other contributing causes",
                     "What makes it worse", "What can be done"],
    },
    "howto": {
        "lead": "the fastest correct way, in one sentence",
        "sections": ["The short answer", "Step by step", "Things that go wrong",
                     "How to check it worked", "Going further"],
    },
    "comparison": {
        "lead": "the decisive difference, in one sentence",
        "sections": ["The key difference", "Side by side", "When each is right",
                     "Common mix-ups", "Rule of thumb"],
    },
    "list": {
        "lead": "how many, and the most important one first",
        "sections": ["The list", "Why each one matters", "Which matters most"],
    },
    "opinion": {
        "lead": "a direct recommendation, in one sentence",
        "sections": ["My recommendation", "Why", "What could go wrong",
                     "How to decide for yourself"],
    },
    "wide": {
        "lead": "a plain-language overview paragraph",
        "sections": ["Overview", "Key facts", "How it works", "History",
                     "Types or forms", "Real-world impact", "Debates and limits",
                     "Common questions"],
    },
    "general": {
        "lead": "the direct answer in the first two sentences",
        "sections": ["Direct answer", "Details", "Examples", "Limits"],
    },
}

VERBOSITY = {
    "quick": (1, 2),
    "standard": (2, 3),
    "deep": (3, 5),
    "exhaustive": (4, 8),
}


def blueprint(intent: str, depth: str = "deep") -> Dict[str, Any]:
    bp = BLUEPRINTS.get(intent) or BLUEPRINTS["general"]
    lo, hi = VERBOSITY.get(depth, (2, 4))
    return {"lead": bp["lead"], "sections": bp["sections"][:hi]}


# ---------------------------------------------------------------------------
# memory helpers used by the "personal" intent and by RyzekMemory
# ---------------------------------------------------------------------------

# A name is one or two capitalised words. Anything longer is a sentence, not a name.
_NAME_STOP = {"and", "but", "also", "so", "or", "i", "im", "i'm", "my", "from",
              "in", "at", "live", "work", "study", "am", "is", "are", "here",
              "there", "please", "thanks", "thank", "you", "we", "he", "she"}
# One name word, optionally a second one that is NOT a joining word.
_WORD = r"[A-Za-z][A-Za-z'\-]*"
_NAME_PATTERNS = [
    re.compile(r"\bmy name is\s+(" + _WORD + r"(?:\s+(?!and\b|but\b|also\b|so\b|or\b|"
               r"i\b|i'm\b|my\b|from\b|in\b|at\b|who\b|please\b)" + _WORD + r")?)", re.I),
    re.compile(r"\bcall me\s+(" + _WORD + r"(?:\s+(?!and\b|but\b|also\b|so\b|or\b|"
               r"i\b|i'm\b|my\b|please\b)" + _WORD + r")?)", re.I),
    re.compile(r"\bmera naam\s+(" + _WORD + r"(?:\s+(?!and\b|hai\b|he\b)" + _WORD + r")?)", re.I),
    re.compile(r"\bi am\s+([A-Z]" + _WORD[1:] + r"(?:\s+[A-Z]" + _WORD[1:] + r")?)", 0),
    re.compile(r"\bi'm\s+([A-Z]" + _WORD[1:] + r"(?:\s+[A-Z]" + _WORD[1:] + r")?)", 0),
]


def find_name(text: str) -> Optional[str]:
    for pat in _NAME_PATTERNS:
        m = pat.search(text or "")
        if not m:
            continue
        name = m.group(1).strip(" .,-")
        words = [w for w in name.split() if w]
        if not words or any(w.lower().strip("'") in _NAME_STOP for w in words):
            continue
        if len(words) > 2 or not (2 <= len(name) <= 30):
            continue
        return " ".join(w[:1].upper() + w[1:] if w.islower() else w for w in words)
    return None


def personal_query(text: str) -> Optional[str]:
    """Map a personal question to a stored fact key, if we know it."""
    low = (text or "").lower()
    table = [
        (r"\bmy name\b|\bwho am i\b|\bwhat am i called\b", "name"),
        (r"\bmy favou?rite colour\b|\bmy favou?rite color\b", "favourite_colour"),
        (r"\bmy favou?rite (food|dish)\b", "favourite_food"),
        (r"\bmy (job|work|profession)\b|\bwhat do i do\b", "job"),
        (r"\bmy (city|town|location)\b|\bwhere do i live\b", "city"),
        (r"\bmy (goal|aim|target)\b|\bwhat am i working (on|towards)\b", "goal"),
        (r"\bmy (hobby|hobbies)\b", "hobby"),
        (r"\bmy (school|college|university)\b", "school"),
        (r"\bmy (birthday|birth date)\b", "birthday"),
        (r"\bmy (language|mother tongue)\b", "language"),
    ]
    for pat, key in table:
        if re.search(pat, low):
            return key
    m = re.search(r"\bmy (favou?rite\s+[a-z ]{2,20}?)\b", low)
    if m:
        return "favourite_" + re.sub(r"[^a-z]+", "_", m.group(1).replace("favourite", "")
                                     .replace("favorite", "").strip()).strip("_")
    return None


def recall_intro(name: Optional[str]) -> str:
    if name:
        return f"Yes - I remember you, **{name}**."
    return "Yes - I keep a memory of our chats."


def split_sentences(text: str) -> List[str]:
    parts = re.split(r"(?<=[.!?])\s+", re.sub(r"\s+", " ", text or "").strip())
    return [p.strip() for p in parts if len(p.strip()) > 2]


def summarise_turns(turns: List[Tuple[str, str]], limit: int = 5) -> List[str]:
    """Turn remembered Q/A pairs into short bullet lines."""
    out = []
    for question, answer in turns[:limit]:
        q = re.sub(r"\s+", " ", question).strip()
        first = (split_sentences(re.sub(r"[#*`>]", "", answer or "")) or [""])[0]
        out.append(f"**You asked:** {q[:120]}" + (f"\n  → {first[:170]}" if first else ""))
    return out
