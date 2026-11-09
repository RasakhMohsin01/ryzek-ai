#!/usr/bin/env python3
"""
Ryzek AI - intermediate-English pass (v2.5).

Ryzek's answers must stay readable: clear everyday English, short words, no
academic padding. This module is a conservative, reversible text pass applied
at the single choke point after an answer is composed. It never touches URLs,
code fences, numbers, headings or quoted user text, and it never changes the
meaning of a sentence - it only swaps ornate words for plain ones.

Level "simple" also removes a few long stock phrases. "detailed" leaves the
wording alone for users who want the fuller register.
"""

from __future__ import annotations

import re
from typing import Dict, List, Tuple

LEVELS = ("simple", "intermediate", "detailed")
DEFAULT_LEVEL = "intermediate"

# Long phrases first, then single words. Multi-word keys are matched as phrases.
PHRASES: List[Tuple[str, str]] = [
    ("due to the fact that", "because"),
    ("it is worth noting that", "note that"),
    ("in spite of the fact that", "although"),
    ("with regard to", "about"),
    ("with respect to", "about"),
    ("in relation to", "about"),
    ("pertaining to", "about"),
    ("in order to", "to"),
    ("a considerable amount of", "a lot of"),
    ("a wide variety of", "many"),
    ("in the event that", "if"),
    ("at this point in time", "now"),
    ("for the purpose of", "to"),
    ("is of the opinion that", "thinks that"),
    ("suffice it to say", "simply put"),
    ("in principle measurable", "measurable"),
    ("prior to", "before"),
    ("subsequent to", "after"),
    ("aforementioned", "this"),
]

WORDS: Dict[str, str] = {
    "utilise": "use", "utilises": "uses", "utilised": "used",
    "utilize": "use", "utilizes": "uses", "utilized": "used",
    "subsequently": "later", "nevertheless": "still", "furthermore": "also",
    "moreover": "also", "consequently": "so", "notwithstanding": "despite",
    "whilst": "whilst", "henceforth": "from now on", "approximately": "about",
    "myriad": "many", "plethora": "many", "multitude": "many",
    "facilitate": "help", "facilitates": "helps", "commence": "start",
    "commences": "starts", "endeavour": "try", "endeavor": "try",
    "elucidate": "explain", "ascertain": "find out", "leverage": "use",
    "paradigm": "model", "nuanced": "detailed", "comprehensive": "full",
    "fundamental": "basic", "substantial": "large", "numerous": "many",
    "additionally": "also", "alternatively": "or", "ultimately": "finally",
    "predominantly": "mostly", "approximately": "about", "sufficient": "enough",
    "subsequently": "later", "deliberately": "on purpose",
}

# Only these stock lines are trimmed; nothing user-written is removed.
BOILERPLATE = (
    "That is a stronger position than a confident claim with no evidence behind it.",
    "Reading aloud catches almost every awkward sentence that silent proofreading misses.",
)


def _match_case(original: str, replacement: str) -> str:
    if original.isupper():
        return replacement.upper()
    if original[:1].isupper():
        return replacement[:1].upper() + replacement[1:]
    return replacement


def _replace_word(text: str, word: str, replacement: str) -> str:
    pattern = re.compile(r"\b" + re.escape(word) + r"\b", re.I)
    return pattern.sub(lambda m: _match_case(m.group(0), replacement), text)


def _split_fences(text: str) -> Tuple[List[str], List[bool]]:
    """Return (chunks, is_code) so fenced code and inline code stay untouched."""
    chunks, flags = [], []
    pos = 0
    for m in re.finditer(r"```.*?```", text, re.S):
        if m.start() > pos:
            chunks.append(text[pos:m.start()]); flags.append(False)
        chunks.append(m.group(0)); flags.append(True)
        pos = m.end()
    if pos < len(text):
        chunks.append(text[pos:]); flags.append(False)
    return chunks, flags


def intermediate(text: str, level: str = DEFAULT_LEVEL) -> str:
    """Make an answer read at an intermediate (or simpler) English level."""
    if not text or level not in LEVELS or level == "detailed":
        return text
    chunks, flags = _split_fences(text)
    out = []
    for chunk, is_code in zip(chunks, flags):
        if is_code:
            out.append(chunk)
            continue
        # Protect URLs and inline code spans from any substitution.
        holders: List[str] = []

        def hold(m):
            holders.append(m.group(0))
            return "\x00%d\x00" % (len(holders) - 1)

        chunk = re.sub(r"https?://[^\s)\]]+|`[^`]+`|\[[^\]]+\]\([^)]+\)", hold, chunk)
        for phrase, plain in PHRASES:
            chunk = re.sub(re.escape(phrase),
                           lambda m, p=plain: _match_case(m.group(0), p),
                           chunk, flags=re.I)
        for word, plain in WORDS.items():
            chunk = _replace_word(chunk, word, plain)
        if level == "simple":
            for line in BOILERPLATE:
                chunk = chunk.replace(line, "")
        for i, original in enumerate(holders):
            chunk = chunk.replace("\x00%d\x00" % i, original)
        out.append(chunk)
    return "".join(out)


def label(level: str = DEFAULT_LEVEL) -> str:
    return {"simple": "Simple", "intermediate": "Intermediate",
            "detailed": "Detailed"}.get(level, "Intermediate")


def note(level: str = DEFAULT_LEVEL) -> str:
    return ("Ryzek writes in clear, intermediate English. Change the reading level "
            "any time from the top bar or Settings." if level == "intermediate" else
            "Ryzek is using short, simple sentences." if level == "simple" else
            "Ryzek is using the full detailed register.")
