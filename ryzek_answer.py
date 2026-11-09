#!/usr/bin/env python3
"""
Ryzek AI v2.6 - the composer that writes like an assistant, not like a search page.

The old path dropped raw BM25 passages into a boilerplate skeleton, which is why
"why does my phone battery drain fast" came back as "What this question is really
asking" instead of an actual answer.

This module works from a `Build` object:

    lead         a short, direct answer written from the best sentence(s)
    sections     headings + bullet points that each carry a real fact
    taken from   the sources actually used
    next         one useful follow-up offer

Everything is derived from material supplied by the caller (curated knowledge,
live pages, the reasoning engine, the user's own memory), so no sentence is
invented. If there is genuinely not enough material, `Build.confident` is False
and the caller decides what to do instead of pretending.
"""

from __future__ import annotations

import html
import re
from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, List, Optional, Tuple

import ryzek_understand as understand

SENT_SPLIT = re.compile(r"(?<=[.!?])\s+(?=[A-Z0-9\"'(])")

# Sentences that carry no information for an answer.
_JUNK = re.compile(
    r"(cookie|privacy policy|subscribe|newsletter|advertisement|sign in|log in|"
    r"click here|read more|all rights reserved|share this|follow us|"
    r"javascript|enable js|accessibility|skip to content|"
    r"^(home|menu|search|share|tweet|email)$)", re.I)


def _clean(text: str) -> str:
    text = re.sub(r"\[[0-9]{1,3}\]", "", text)          # wikipedia [12] markers
    text = re.sub(r"\(\s*\)|\[\s*\]", "", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip(" -–—:;,")


def sentences(text: str) -> List[str]:
    out = []
    for raw in SENT_SPLIT.split(_clean(text)):
        s = raw.strip()
        if len(s) < 25 or len(s) > 420:
            continue
        if _JUNK.search(s):
            continue
        if s.count("|") > 1:                            # table rows / nav bars
            continue
        letters = sum(ch.isalpha() for ch in s)
        if letters < len(s) * 0.55:
            continue
        out.append(s)
    return out


def _key_terms(text: str) -> set:
    return set(understand.content_terms(text))


def score(sentence: str, subject_terms: set, wants: Iterable[str]) -> float:
    terms = _key_terms(sentence)
    if not terms:
        return 0.0
    overlap = len(terms & subject_terms)
    s = overlap * 3.0
    # a definition-ish sentence is gold as a lead
    if re.match(r"^(a|an|the)\s+\w+\s+(is|are|refers to|means)\b", sentence, re.I):
        s += 2.0
    if re.search(r"\b(is|are|means|refers to|defined as|consists of|happens because|"
                 r"causes|leads to|results in|because)\b", sentence, re.I):
        s += 1.0
    if re.search(r"\d", sentence):
        s += 0.6
    w = " ".join(wants).lower()
    if "steps" in w and re.search(r"\b(first|then|next|finally|step)\b", sentence, re.I):
        s += 0.8
    if "history" in w and re.search(r"\b(18|19|20)\d\d\b", sentence):
        s += 0.8
    if "pros/cons" in w and re.search(r"\b(benefit|advantage|drawback|risk|however)\b",
                                      sentence, re.I):
        s += 0.8
    # penalise filler and navigational text
    if re.search(r"\b(wikipedia|this article|see also|further reading|citation needed)\b",
                 sentence, re.I):
        s -= 1.2
    if len(sentence) > 320:
        s -= 0.5
    return s


def dedupe(sents: List[str], threshold: float = 0.72) -> List[str]:
    """Drop near-duplicates (same facts repeated by several sites)."""
    kept: List[str] = []
    seen_grams = []
    for s in sents:
        grams = _key_terms(s)
        if not grams:
            continue
        dup = False
        for other in seen_grams:
            if not other:
                continue
            inter = len(grams & other)
            if inter / max(1, len(grams | other)) >= threshold:
                dup = True
                break
        if not dup:
            kept.append(s)
            seen_grams.append(grams)
    return kept


_NOISE_TAIL = re.compile(
    r"\s[-\u2013\u2014|]\s*(?:source|webpages?|duckduckgo|wikipedia|wikidata|"
    r"stack ?overflow|bing|google|britannica|news|reuters|wsj|efinancialcareers)\b", re.I)
_FUNCTION = {"the", "a", "an", "of", "and", "to", "in", "is", "it", "for", "on",
             "with", "that", "as", "by", "at", "its", "was", "are", "be", "how", "why"}


def is_headline(sentence: str) -> bool:
    """True for scraped page titles / news headlines.

    They are not answers: 'As Goldman Sachs restricts vibe coding, developers
    express how annoying it is eFinancialCareers'. Dropping them keeps them out
    of plans and key-point lists where they read like advice.
    """
    s = (sentence or "").strip()
    # never touch code, commands or SQL: those are material too
    if re.search(r"(=>|\bdef\b|\bimport\b|\bSELECT\b|\bFROM\b|&& |\$ |[{};]$|`|\bprint\()", s):
        return False
    words = s.split()
    if len(words) < 3 or len(s) > 170:
        return False
    if _NOISE_TAIL.search(s):
        return True
    caps = sum(1 for w in words if w[:1].isupper())
    funcs = sum(1 for w in words if w.lower().strip(".,:;!?") in _FUNCTION)
    if caps / len(words) >= 0.6 and funcs <= 2:
        return True
    # a headline has no closing stop, an answer sentence does
    if caps / len(words) >= 0.4 and funcs <= 3 and not s.endswith((".", "!", "?", "\"", ":")):
        return True
    # a long run that stops on a brand name instead of punctuation
    stop = (".", "!", "?", "\"", ":", ")", "%", ";", "}", "{", "'", "`", "\u2019", "\u201d")
    if len(words) >= 6 and not s.endswith(stop):
        last = words[-1].strip(",;:-")
        camel = re.search(r"[a-z][A-Z]", last)          # 'eFinancialCareers'
        # 'UTF-8' / 'R2' end in a digit or code, not a brand
        if (last[:1].isupper() or camel) and not re.search(r"\d", last):
            return True
    return False


def best_sentences(material: List[Tuple[str, str]], subject: str,
                   wants: List[str], limit: int = 14,
                   priority: Optional[List[str]] = None) -> List[Tuple[str, str]]:
    """material is [(sentence, source_title)]. Returns the most useful ones.

    `priority` lists source titles that were written and checked by hand; they
    always outrank scraped sentences.
    """
    terms = _key_terms(subject)
    pri = set(priority or [])
    # hand-written library text is never treated as a headline; scraped
    # titles are, so a news headline cannot pose as advice
    scored = [(score(s, terms, wants) + (3.0 if src in pri else 0.0), s, src)
              for s, src in material if s and (src in pri or not is_headline(s))]
    scored.sort(key=lambda x: -x[0])
    picked = [(s, src) for sc, s, src in scored if sc > 0][: limit * 2]
    if len(picked) < 4:
        picked = [(s, src) for _, s, src in scored[: limit]]
    # keep original order for readability, then dedupe
    uniq = dedupe([s for s, _ in picked])
    by_sentence = {}
    for s, src in picked:
        by_sentence.setdefault(s, src)
    return [(s, by_sentence.get(s, "")) for s in uniq][:limit]


_SNIPPET_TAIL = re.compile(
    r"(\u2026|\.\.\.)\s*$|^\s*(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)\s+\d{1,2},?\s+\d{4}\s*\u00b7"
    r"|\b(?:hex|rgb|rgba)\b|#[0-9a-f]{6}\b|\b\d{1,2}\.\d%\s+(?:red|green|blue)", re.I)


def is_snippet(sentence: str) -> bool:
    """Search-result snippets pasted into an answer read like scraped noise.

    They carry dates, ellipses, 'hex #87CEEB' fragments and trailing '…', and
    they are never a good opening line even when they are on topic.
    """
    s = (sentence or "").strip()
    if not s:
        return True
    if _SNIPPET_TAIL.search(s):
        return True
    if s[:1].islower():                       # mid-sentence fragment
        return True
    return False


def first_lead(cands: List[Tuple[str, str]], subject: str,
               priority: Optional[List[str]] = None) -> Optional[str]:
    """Pick the sentence that best introduces the subject.

    Checked, hand-written sources always open the answer when one is present:
    a verified sentence beats a scraped one even if the scraped one scores
    higher on keywords.
    """
    if not cands:
        return None
    pri = set(priority or [])
    trusted = [(s, src) for s, src in cands if src in pri and not is_snippet(s)]
    if trusted:
        cands = trusted
    terms = _key_terms(subject)
    best, best_score = None, -99.0
    for s, _src in cands:
        if is_headline(s) or is_snippet(s):
            continue
        sc = score(s, terms, [])
        if re.match(r"^(a|an|the)\s", s, re.I):
            sc += 1.5
        if subject.split() and subject.split()[0].lower() in s.lower():
            sc += 0.8
        if len(s) > 300:
            sc -= 0.7
        if re.search(r"\b(because|so|which means|this means|is caused|caused by|"
                     r"happens when|results? in|leads? to)\b", s, re.I):
            sc += 1.2                          # an explanation, not a label
        if sc > best_score:
            best, best_score = s, sc
    if best is None:                           # everything looked like a snippet
        best = next((s for s, _ in cands if not is_headline(s)), cands[0][0])
    return best


def wrap(text: str, width: int = 460) -> str:
    """Keep bullets readable: split very long sentences into two lines."""
    text = text.strip()
    if len(text) <= width:
        return text
    parts = re.split(r"(?<=[;,:])\s+", text)
    out, line = [], ""
    for p in parts:
        if len(line) + len(p) > width and line:
            out.append(line)
            line = p
        else:
            line = (line + " " + p).strip()
    if line:
        out.append(line)
    return " ".join(out[:2]) if out else text[:width]


# ---------------------------------------------------------------------------
# the build object
# ---------------------------------------------------------------------------

@dataclass
class Build:
    understanding: understand.Understanding
    lead: str = ""
    sections: List[Tuple[str, List[str]]] = field(default_factory=list)
    used: List[Dict[str, str]] = field(default_factory=list)
    trailing: List[str] = field(default_factory=list)
    confident: bool = True
    tone: str = ""
    header: str = ""

    def render(self, header: Optional[str] = None) -> str:
        u = self.understanding
        lines: List[str] = []
        head = header or self.header
        if head:
            lines.append(head)
            lines.append("")
        if self.lead:
            lines.append(self.lead.strip())
            lines.append("")
        for heading, bullets in self.sections:
            if not bullets:
                continue
            lines.append(f"## {heading}")
            lines.append("")
            for b in bullets:
                lines.append(f"- {b}")
            lines.append("")
        if self.trailing:
            for t in self.trailing:
                lines.append(t)
            lines.append("")
        if self.used:
            lines.append("## Where this comes from")
            lines.append("")
            for s in self.used[:8]:
                if s.get("url"):
                    lines.append(f"- [{s['title']}]({s['url']}) - {s.get('kind', 'source')}")
                else:
                    lines.append(f"- {s['title']} - {s.get('kind', 'source')}")
            lines.append("")
        return "\n".join(lines).strip() + "\n"


def used_sources(picked: List[Tuple[str, str]],
                 sources: List[Dict[str, str]]) -> List[Dict[str, str]]:
    """Only the sources whose sentences made it into the answer, in order."""
    order: List[str] = []
    for _sent, src in picked:
        if src and src not in order:
            order.append(src)
    by_title = {s.get("title"): s for s in sources}
    out = []
    for title in order:
        src = by_title.get(title)
        if src:
            out.append(src)
        elif title:
            out.append({"title": title, "url": "", "kind": "source"})
    return out[:8]


def _bullets(sents: List[str], max_lines: int = 5, width: int = 320) -> List[str]:
    out = []
    for s in sents[:max_lines]:
        if len(s) > 300:
            # split at a natural break so a bullet stays scannable
            cut = max(s.rfind(", ", 0, 240), s.rfind("; ", 0, 240),
                      s.rfind(" because ", 0, 240))
            if cut > 120:
                out.append(wrap(s[:cut + 1].strip(), width))
                out.append(wrap(s[cut + 1:].strip(), width))
                continue
        out.append(wrap(s, width))
    return out[: max_lines + 2]


# ---------------------------------------------------------------------------
# builders per intent
# ---------------------------------------------------------------------------

def build_general(u: understand.Understanding, material: List[Tuple[str, str]],
                  sources: List[Dict[str, str]], depth: str = "deep",
                  priority: Optional[List[str]] = None) -> Build:
    """definition / cause / howto / comparison / list / opinion / wide / general."""
    bp = understand.blueprint(u.intent, depth)
    subject = u.subject or u.clean
    picked = best_sentences(material, subject, u.wants,
                            limit=18 if depth == "exhaustive" else 12,
                            priority=priority)
    b = Build(understanding=u, used=used_sources(picked, sources))
    if not picked:
        b.confident = False
        return b

    lead = first_lead(picked, subject, priority)
    used_lead = False
    if lead:
        b.lead = ensure_answer_start(lead, u)
        used_lead = True
    rest = [s for s, _ in picked if s != lead]

    n_headings = len(bp["sections"])
    per = max(2, (len(rest) + n_headings - 1) // max(1, n_headings)) if rest else 2
    idx = 0
    for name in bp["sections"]:
        chunk = rest[idx: idx + per]
        idx += per
        if not chunk:
            break
        b.sections.append((name, _bullets(chunk, max_lines=4 if depth != "exhaustive" else 5)))

    # Depth spine: longer answers also get the classic sections, so an
    # exhaustive answer really is exhaustive.
    if depth in ("deep", "exhaustive") and len(picked) > 10:
        deep_sections = ([("In detail", "detail"), ("Key points", "points"),
                          ("Common questions", "questions")]
                         if depth == "deep" else
                         [("In detail", "detail"), ("Key points", "points"),
                          ("Common questions", "questions"),
                          ("Glossary of key terms", "glossary")])
        remaining = rest[idx:]
        per_deep = max(2, len(remaining) // max(1, len(deep_sections)))
        j = 0
        for name, kind in deep_sections:
            chunk = extra_chunk(picked, kind) if kind in ("points", "glossary") \
                else remaining[j: j + per_deep]
            j += per_deep
            if name == "Glossary of key terms":
                gloss = glossary(picked, u.subject)
                if gloss:
                    b.sections.append((name, gloss))
                continue
            if chunk:
                b.sections.append((name, _bullets(chunk, max_lines=5)))

    # Always offer the obvious next step.
    b.trailing.append(next_step_line(u))
    if not used_lead and not b.lead:
        b.confident = False
    # Long answers keep the familiar spine so they read like a proper report.
    if len(picked) > 8:
        lead_head = "## Short answer" if depth != "quick" else "## Quick answer"
        b.header = lead_head
    return b


def ensure_answer_start(sentence: str, u: understand.Understanding) -> str:
    """Make the lead read like an answer, not like a fragment."""
    s = sentence.strip()
    if re.match(r"^(it|this|they|these|those|he|she|there)\b", s, re.I) and u.subject:
        # replace a dangling pronoun with the subject so the lead stands alone
        subj = u.subject.split(" vs ")[0]
        s = re.sub(r"^(It|This|They|These|Those)\b", subj.capitalize(), s, count=1)
    return s


def next_step_line(u: understand.Understanding) -> str:
    subject = (u.subject or "").split(" vs ")[0][:40]
    if u.intent == "cause":
        return ("**Want the fix?** Ask \"so what should I do about it?\" and I'll turn this "
                "into steps you can follow.")
    if u.intent == "howto":
        return ("**Want it deeper?** Say \"more detail on the first step\" and I'll expand "
                "that part.")
    if u.intent == "comparison":
        return ("**Want a test case?** Give me a real sentence and I'll tell you which one "
                "fits and why.")
    if u.intent == "opinion":
        return ("**Want it tailored?** Tell me your budget, time limit or skill level and "
                "I'll make the advice specific.")
    if subject:
        return (f"**Next:** ask \"give me examples of {subject}\" or "
                f"\"what is the history of {subject}\".")
    return "**Next:** give me one more detail and I'll narrow this down."


def build_wide(u: understand.Understanding, material: List[Tuple[str, str]],
               sources: List[Dict[str, str]], depth: str = "deep",
               priority: Optional[List[str]] = None) -> Build:
    """'tell me everything about X' -> a full, ordered overview."""
    subject = u.subject or u.clean
    picked = best_sentences(material, subject, u.wants + ["history"], limit=30,
                            priority=priority)
    b = Build(understanding=u, used=used_sources(picked, sources))
    if len(picked) < 4:
        b.confident = False
        return b
    lead = first_lead(picked, subject, priority)
    b.lead = ensure_answer_start(lead, u) if lead else ""
    rest = [s for s, _ in picked if s != lead]

    # group by the strongest theme word in each sentence
    groups: Dict[str, List[str]] = {}
    order: List[str] = []
    for s in rest:
        theme = theme_of(s, subject)
        if theme not in groups:
            groups[theme] = []
            order.append(theme)
        groups[theme].append(s)
    for theme in order[:8]:
        b.sections.append((theme, _bullets(groups[theme], max_lines=4)))
    if len(b.sections) < 2:
        # fall back to a plain split so the answer still has structure
        half = max(1, len(rest) // 2)
        b.sections = [("Key facts", _bullets(rest[:half])),
                      ("More detail", _bullets(rest[half:]))]
    b.sections.append(("The short version",
                       ["If you only remember one thing: " +
                        wrap(rest[0] if rest else b.lead, 300)]))
    b.trailing.append("**Narrow it down:** ask about any section above and I'll go deep on it.")
    return b


_THEMES: List[Tuple[str, str]] = [
    ("What it is", r"\b(is|are|refers to|means|defined as|consists of)\b"),
    ("How it works", r"\b(works?|process|mechanism|functions?|operates?|through)\b"),
    ("How it started", r"\b(first|invented|discovered|originally|19\d\d|18\d\d|history|created)\b"),
    ("Types and forms", r"\b(types?|kinds?|forms?|categories|classified)\b"),
    ("Where you see it", r"\b(used|use|found in|such as|for example|applications?|industry)\b"),
    ("Numbers that matter", r"\b\d+(\.\d+)?\s*(%|percent|million|billion|km|kg|m/s)?\b"),
    ("Risks and limits", r"\b(risk|danger|problem|however|limit|drawback|concern|but)\b"),
    ("What people debate", r"\b(debate|critic|argue|some say|controvers|dispute)\b"),
]


def theme_of(sentence: str, subject: str) -> str:
    for name, pat in _THEMES:
        if re.search(pat, sentence, re.I):
            return name
    return "More detail"


def extra_chunk(picked: List[Tuple[str, str]], kind: str) -> List[str]:
    """Short, punchy sentences for the 'Key points' section."""
    out = []
    for sent, _src in picked:
        if is_snippet(sent) or is_headline(sent):
            continue
        if len(sent) <= 170 and re.search(r"\d", sent) and len(out) < 4:
            out.append(wrap(sent, 300))
    if not out:
        out = [wrap(s, 300) for s, _ in picked[:3]]
    return out


def glossary(picked: List[Tuple[str, str]], subject: str) -> List[str]:
    """Define the recurring technical nouns that appear in the material."""
    counts: Dict[str, int] = {}
    for sent, _src in picked:
        for term in re.findall(r"\b([A-Z][a-z]{3,}(?:\s+[a-z]{3,})?)\b", sent):
            key = term.strip()
            if key.lower() in ("the", "this", "these", "that"):
                continue
            counts[key] = counts.get(key, 0) + 1
    terms = [t for t, n in sorted(counts.items(), key=lambda x: -x[1]) if n >= 2][:6]
    out = []
    for term in terms:
        for sent, _src in picked:
            if term in sent and re.search(r"\b(is|are|means|refers to)\b", sent):
                out.append(f"**{term}:** {wrap(sent, 260)}")
                break
    return out


def build_step_guide(u: understand.Understanding, material: List[Tuple[str, str]],
                     sources: List[Dict[str, str]],
                     priority: Optional[List[str]] = None) -> Build:
    """Turn material into an actual numbered plan for how-to questions."""
    picked = best_sentences(material, u.subject or u.clean, u.wants + ["steps"],
                            limit=16, priority=priority)
    b = Build(understanding=u, used=used_sources(picked, sources))
    if not picked:
        b.confident = False
        return b
    lead = first_lead(picked, u.subject, priority)
    if lead:
        b.lead = ensure_answer_start(lead, u)
    steps = [s for s, _ in picked if s != lead][:7]
    b.sections.append(("Do this, in order",
                       [wrap(s, 300) for s in steps] or [wrap(lead or "", 300)]))
    b.trailing.append("**If one step doesn't work,** tell me which one and I'll troubleshoot it with you.")
    return b


# ---------------------------------------------------------------------------
# memory answers
# ---------------------------------------------------------------------------

def build_memory_answer(u: understand.Understanding, facts: List[Dict[str, Any]],
                        questions: List[Dict[str, Any]],
                        name: Optional[str]) -> str:
    """Answer 'what do you remember?' / 'what did I ask?' from real stored rows."""
    lines: List[str] = []
    if u.intent == "personal" and not questions:
        key_probe = understand.personal_query(u.original)
        if facts or name:
            hit = None
            if key_probe:
                hit = next((f for f in facts if f["key"] == key_probe), None)
            if hit:
                lines.append(f"## Your {hit['key'].replace('_', ' ')}")
                lines.append("")
                lines.append(f"You told me: **{hit['value']}**.")
                lines.append("")
                lines.append("*I keep this in this account's memory, so it is still here "
                             "next time you log in.*")
                return "\n".join(lines)
            # a stored note ("my exam is on 12 May") answers any wording of it
            notes = [f for f in facts if f["key"].startswith("note_")]
            terms = set(understand.content_terms(u.original))
            hit_note = None
            for f in notes:
                if terms and len(terms & set(understand.content_terms(f["value"]))) >= 2:
                    hit_note = f
                    break
            if hit_note:
                lines.append("## From my memory of you")
                lines.append("")
                lines.append(f"You asked me to remember: **{hit_note['value']}**.")
                lines.append("")
                return "\n".join(lines)
            if key_probe:
                pretty = key_probe.replace("_", " ")
                lines.append(f"## I don't know your {pretty} yet")
                lines.append("")
                lines.append(f"You haven't told me your {pretty} in this account. "
                             f"Say \"my {pretty} is ...\" and I'll remember it.")
                lines.append("")
                if facts:
                    lines.append("## What I do remember")
                    lines.append("")
                    for f in facts[:8]:
                        lines.append(f"- **{f['key'].replace('_', ' ')}:** {f['value']}")
                return "\n".join(lines)

    if name:
        lines.append(f"Yes - I remember you, **{name}**.")
    else:
        lines.append("Here is everything I have kept from your chats.")
    lines.append("")
    if facts:
        lines.append("## Things you told me")
        lines.append("")
        for f in facts[:12]:
            label = "note" if f["key"].startswith("note_") else f["key"].replace("_", " ")
            lines.append(f"- **{label}:** {f['value']}")
        lines.append("")
    if questions:
        lines.append("## Questions you asked me")
        lines.append("")
        for row in questions[:8]:
            q = row["question"].strip()
            a = (row.get("answer") or "").strip()
            lines.append(f"- **{q[:110]}**")
            if a:
                lines.append(f"  - I answered: {a[:160]}")
        lines.append("")
    if not facts and not questions:
        lines.append("Nothing yet - this account has no stored memories. Tell me your name, "
                     "your city or what you are working on and I'll keep it.")
        lines.append("")
    lines.append("## Memory controls")
    lines.append("")
    lines.append("- **See this again:** ask \"what do you remember about me?\"")
    lines.append("- **Erase it:** open Settings and press *Forget everything*, or type `/forget`.")
    lines.append("- **Scope:** memories belong to *this account* only - other accounts cannot see them.")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# fallbacks that still stay honest
# ---------------------------------------------------------------------------

def honest_fallback(u: understand.Understanding, depth: str = "deep") -> str:
    """Used only when there is genuinely no usable material.

    Short, specific and useful - never a generic 'framework' essay.
    """
    subject = u.subject or u.clean
    lines = [f"I don't have reliable material on **{subject}** yet, so I won't guess."]
    lines.append("")
    lines.append("## Two things that will get you a real answer")
    lines.append("")
    lines.append(f"1. **Give me one more detail** - a date, a field, a brand, a country. "
                 f"For example: \"{subject} in 2024\" or \"{subject} for beginners\".")
    lines.append(f"2. **Switch on live web** (top bar) so I can read today's pages instead of "
                 f"only my local knowledge.")
    lines.append("")
    lines.append("## Try me on something concrete")
    lines.append("")
    lines.append("- \"explain how a refrigerator works\"")
    lines.append("- \"why does my phone get hot while charging\"")
    lines.append("- \"compare diesel and petrol cars\"")
    return "\n".join(lines)
