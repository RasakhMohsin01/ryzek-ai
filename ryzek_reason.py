#!/usr/bin/env python3
"""
Ryzek AI - numerical, logical and analytical reasoning.

These are deterministic solvers, not guesses: each one computes the answer,
shows the steps, and states the assumption it used. If no solver recognises the
question, `solve()` returns None and the normal research pipeline takes over.
"""

from __future__ import annotations

import math
import re
from typing import Dict, List, Optional, Tuple

NUM = r"-?\d+(?:\.\d+)?"
NUM_RE = re.compile(NUM)


def _nums(text: str) -> List[float]:
    return [float(x) for x in NUM_RE.findall(text or "")]


def _fmt(x: float) -> str:
    if abs(x - round(x)) < 1e-9:
        return str(int(round(x)))
    return f"{x:g}"


def _wrap(title: str, short: str, steps: List[str], checks: List[str],
          depth: str, assumption: str = "", extra: str = "") -> str:
    out = [f"## {title}", "", short]
    if assumption:
        out += ["", f"**Assumption:** {assumption}"]
    out += ["", "## Worked steps", ""]
    for i, step in enumerate(steps, 1):
        out.append(f"{i}. {step}")
    if depth != "quick":
        out += ["", "## Why this works", "", extra or
                "Each step follows from the previous one by a stated rule, so the result can be "
                "checked by hand rather than taken on trust.", "",
                "## Common mistakes and limits", ""]
        for c in checks:
            out.append(f"- {c}")
    if depth in ("deep", "exhaustive"):
        out += ["", "## Sanity check", "",
                f"Result: **{short}**. Re-derive it with a different method (a diagram, a smaller "
                "example, or working backwards); if both methods agree, the reasoning is sound.", "",
                "## Sources", "",
                "- Deterministic computation in `ryzek_reason.py` - no external data used.", "",
                "## What I could not verify", "",
                "This answer follows from the information in your question. If a real-world detail "
                "in the problem is different, tell me and I will recompute it."]
    if depth == "exhaustive":
        out += ["", "## Generalisation", "",
                "The method is not specific to these numbers or words. Replace the values with "
                "symbols, solve the general case, then substitute back. A sequence becomes a "
                "recurrence relation; an ordering becomes a directed graph and a topological "
                "sort; a syllogism becomes set inclusion with a closure operator; a decision "
                "becomes a weighted score with a sensitivity analysis.", "",
                "## Edge cases and failure modes", "",
                "- Empty or single-element inputs: most rules need at least three terms to be "
                "identifiable, so say 'not determined' rather than guessing.",
                "- Equal values, zero denominators, negative ratios and cyclic comparisons can "
                "break the naive method; check for them before applying it.",
                "- Contradictory premises make a classical logic problem trivial but misleading: "
                "report the contradiction instead of deriving an arbitrary conclusion.",
                "- Very large or very small numbers can overflow or lose precision; use exact "
                "integer arithmetic or symbolic algebra where it matters.", "",
                "## Cross-check with a second method", "",
                "1. Work backwards from the result to the inputs and confirm every step is "
                "reversible where it should be.",
                "2. Try a brute-force or enumerative check on a small instance.",
                "3. Ask whether a different, equally simple rule fits the same data - if so, "
                "state the ambiguity explicitly.", "",
                "## How to explain this to someone else", "",
                "Start with the answer, then the one rule that produces it, then one worked "
                "example. Leave the caveats until last. If you cannot state the rule in a single "
                "sentence, you do not yet have a solution - you have a pattern you noticed."]
    out += ["", "## Keep going", "",
            "Give me a harder version, ask for the general formula, or ask me to turn this into "
            "a short Python function."]
    return "\n".join(out)


# ---------------------------------------------------------------------------
# Number sequences
# ---------------------------------------------------------------------------


def _next_terms(seq: List[float], count: int = 2) -> Optional[Tuple[str, List[float], List[str]]]:
    n = len(seq)
    if n < 4:
        return None
    ints = all(abs(x - round(x)) < 1e-9 for x in seq)
    vals = [int(round(x)) for x in seq] if ints else seq

    diffs = [vals[i + 1] - vals[i] for i in range(n - 1)]
    if all(abs(d - diffs[0]) < 1e-9 for d in diffs):
        d = diffs[0]
        return ("arithmetic (constant difference)",
                [vals[-1] + d * k for k in range(1, count + 1)],
                [f"Differences: {', '.join(_fmt(x) for x in diffs)} - all equal {_fmt(d)}.",
                 f"Add {_fmt(d)} repeatedly: {', '.join(_fmt(vals[-1] + d * k) for k in range(1, count + 1))}."])

    if ints and all(x != 0 for x in vals[:-1]):
        ratios = [vals[i + 1] / vals[i] for i in range(n - 1)]
        if all(abs(r - ratios[0]) < 1e-9 for r in ratios):
            r = ratios[0]
            return ("geometric (constant ratio)",
                    [vals[-1] * (r ** k) for k in range(1, count + 1)],
                    [f"Ratios: {', '.join(_fmt(x) for x in ratios)} - all equal {_fmt(r)}.",
                     f"Multiply by {_fmt(r)} repeatedly."])

    if ints and n >= 4 and all(abs(vals[i + 2] - (vals[i] + vals[i + 1])) < 1e-9
                               for i in range(n - 2)):
        a, b = vals[-2], vals[-1]
        out = []
        for _ in range(count):
            a, b = b, a + b
            out.append(b)
        return ("Fibonacci-style (each term is the sum of the previous two)",
                out, [f"Check: {_fmt(vals[0])} + {_fmt(vals[1])} = {_fmt(vals[2])}, "
                      f"{_fmt(vals[1])} + {_fmt(vals[2])} = {_fmt(vals[3])}.",
                      f"Continue: {', '.join(_fmt(x) for x in out)}."])

    if ints:
        roots = [int(round(math.sqrt(abs(x)))) for x in vals]
        if all(roots[i] * roots[i] == abs(vals[i]) for i in range(n)):
            base = [int(round(math.sqrt(abs(x)))) for x in vals]
            step = base[1] - base[0]
            if all(base[i + 1] - base[i] == step for i in range(n - 1)):
                nxt = [(base[-1] + step * k) ** 2 for k in range(1, count + 1)]
                return ("squares of an arithmetic sequence", nxt,
                        [f"Square roots: {', '.join(str(x) for x in base)} (step {step}).",
                         f"Square the next roots: {', '.join(str(x) for x in nxt)}."])

    # second differences constant -> quadratic
    second = [diffs[i + 1] - diffs[i] for i in range(len(diffs) - 1)]
    if len(second) >= 2 and all(abs(x - second[0]) < 1e-9 for x in second):
        d2 = second[0]
        next_diff = diffs[-1] + d2
        out, cur, d = [], vals[-1], next_diff
        for _ in range(count):
            cur += d
            out.append(cur)
            d += d2
        return ("quadratic (constant second difference)", out,
                [f"First differences: {', '.join(_fmt(x) for x in diffs)}.",
                 f"Second differences are constant at {_fmt(d2)}, so extend the difference row."])
    return None


def _sequence(text: str, depth: str) -> Optional[str]:
    if not re.search(r"\b(next|continue|sequence|series|pattern|comes next|what follows)\b", text, re.I):
        return None
    nums = _nums(text)
    if len(nums) < 4:
        return None
    # Only treat the contiguous leading list as the sequence.
    m = re.search(r"((?:" + NUM + r"\s*[,;]\s*){3,}" + NUM + r")", text)
    seq = _nums(m.group(1)) if m else nums[:6]
    if len(seq) < 4:
        return None
    solved = _next_terms(seq, 2)
    if not solved:
        return (_wrap("Sequence analysis", "I cannot infer a unique next term from this sequence.",
                      [f"I read the terms as {', '.join(_fmt(x) for x in seq)}.",
                       "I tested constant differences, constant ratios, Fibonacci-style addition, "
                       "squares and constant second differences; none fits all terms."],
                      ["Any finite list of numbers can be extended by infinitely many rules.",
                       "Without a stated rule, the honest answer is that the next term is not determined.",
                       "Give me one more term or the rule and I will continue it exactly."],
                      depth, "The numbers you gave are the whole sequence, in the order written."))
    kind, nxt, steps = solved
    short = f"The next term is **{_fmt(nxt[0])}**; the one after that is **{_fmt(nxt[1])}**."
    steps = [f"I read the sequence as {', '.join(_fmt(x) for x in seq)}."] + steps + [
        f"Pattern identified: {kind}."]
    return _wrap("Sequence solved", short, steps,
                 ["Assuming a different rule (for example a periodic pattern) can give a different "
                  "answer from the same numbers.",
                  "Check that the rule holds for every term, not just the first two.",
                  "Rounding a decimal sequence can hide a genuine pattern."],
                 depth, "The list follows a single consistent rule.",
                 "A finite sequence never proves a rule uniquely, but the simplest rule that fits "
                 "every term is the standard answer. I state the rule so you can reject it if you "
                 "intended a different one.")


# ---------------------------------------------------------------------------
# Ordering / comparison puzzles
# ---------------------------------------------------------------------------

_GREATER = re.compile(
    r"\b([A-Z][A-Za-z]{0,18}|[a-z]{1,18})\s+(?:is|are)\s+"
    r"(taller|older|bigger|larger|faster|heavier|richer|longer|higher|stronger|"
    r"shorter|younger|smaller|slower|lighter|lower|weaker|cheaper|colder|warmer)"
    r"\s+than\s+([A-Z][A-Za-z]{0,18}|[a-z]{1,18})\b", re.IGNORECASE)
_POSITIVE = {"taller", "older", "bigger", "larger", "faster", "heavier", "richer",
             "longer", "higher", "stronger", "warmer"}
_NEGATIVE = {"shorter", "younger", "smaller", "slower", "lighter", "lower", "weaker",
             "cheaper", "colder"}
_QUESTION = re.compile(
    r"\b(who|which|what)\b.*\b(tallest|oldest|biggest|largest|fastest|heaviest|richest|"
    r"longest|highest|strongest|shortest|youngest|smallest|slowest|lightest|lowest|"
    r"weakest|cheapest|coldest|warmest|order|rank)", re.IGNORECASE)


def _ordering(text: str, depth: str) -> Optional[str]:
    pairs = _GREATER.findall(text)
    if len(pairs) < 2 or not _QUESTION.search(text):
        return None
    greater: Dict[str, set] = {}
    entities: List[str] = []
    statements = []
    for a, word, b in pairs:
        a, b, word = a.strip().lower(), b.strip().lower(), word.lower()
        if a == b:
            continue
        for e in (a, b):
            if e not in entities:
                entities.append(e)
        hi, lo = (a, b) if word in _POSITIVE else (b, a)
        greater.setdefault(hi, set()).add(lo)
        statements.append(f"{a.title()} is {word} than {b.title()} → {hi.title()} > {lo.title()}")
    # transitive closure
    changed = True
    while changed:
        changed = False
        for hi in list(greater):
            for mid in list(greater[hi]):
                for lo in greater.get(mid, set()):
                    if lo not in greater[hi]:
                        greater[hi].add(lo)
                        changed = True

    def beats(x: str, y: str) -> bool:
        return y in greater.get(x, set())

    known = [e for e in entities if any(beats(e, o) or beats(o, e) for o in entities if o != e)]
    top = [e for e in known if all(beats(e, o) for o in known if o != e)]
    bottom = [e for e in known if all(beats(o, e) for o in known if o != e)]
    if len(top) == 1:
        short = f"**{top[0].title()}** is the top of the ordering, and **{bottom[0].title()}** is at the bottom." if len(bottom) == 1 else f"**{top[0].title()}** is the top of the ordering."
    elif top:
        short = "The top is tied between " + ", ".join(e.title() for e in top) + "."
    else:
        short = "The information given does not determine a single overall ordering."
    ordered = sorted(known, key=lambda e: -len(greater.get(e, set())))
    steps = statements + [
        "Chain the comparisons transitively: if A > B and B > C, then A > C.",
        "Order: " + " > ".join(e.title() for e in ordered) + ".",
        f"Top candidate(s): {', '.join(e.title() for e in top) or 'not uniquely determined'}."
    ]
    return _wrap("Ordering puzzle solved", short, steps,
                 ["A word like 'shorter' reverses the direction of the comparison.",
                  "If the statements form a cycle or leave two items unconnected, no unique "
                  "winner exists.",
                  "These are relative claims only - they say nothing about absolute values."],
                 depth, "Every comparison describes the same property (for example height).",
                 "This is a transitive ordering problem. I convert every sentence into a directed "
                 "relation, take the transitive closure, then look for an item that dominates all "
                 "the others.")


# ---------------------------------------------------------------------------
# Syllogisms / categorical logic
# ---------------------------------------------------------------------------


def _forms(w: str) -> frozenset:
    """Plural/singular aliases so made-up words chain correctly."""
    w = (w or "").lower().strip().strip(".,!?;:")
    out = {w}
    if len(w) > 3:
        if w.endswith("ies"):
            out |= {w[:-3] + "y", w[:-1]}
        elif w.endswith("es"):
            out |= {w[:-2], w[:-1]}
        elif w.endswith("s"):
            out |= {w[:-1]}
        if w.endswith("y"):
            out |= {w[:-1] + "ies", w[:-1] + "ie"}
        if w.endswith("ie"):
            out |= {w[:-2] + "y", w[:-1] + "s"}
    return frozenset(out)


_ALL = re.compile(r"\b(?:all|every|each)\s+([\w'-]+)\s+(?:is|are|was|were)\s+(?:a|an|the)?\s*([\w'-]+)", re.I)
_NONE = re.compile(r"\bno\s+([\w'-]+)\s+(?:is|are|was|were)\s+(?:a|an|the)?\s*([\w'-]+)", re.I)
_SOME = re.compile(r"\bsome\s+([\w'-]+)\s+(?:is|are|was|were)\s+(?:a|an|the)?\s*([\w'-]+)", re.I)
_INSTANCE = re.compile(r"\b([A-Z][A-Za-z]{1,18}|[a-z]{2,18})\s+is\s+(?:a|an|the)\s+([\w'-]+)\b")
_QUERY = re.compile(r"\b(?:is|are)\s+(?:a|an|the)?\s*([\w'-]+)\s+(?:a|an|the)?\s*([\w'-]+)\s*\?", re.I)


def _syllogism(text: str, depth: str) -> Optional[str]:
    rules = [("all", a, b, _forms(a), _forms(b)) for a, b in _ALL.findall(text)]
    rules += [("none", a, b, _forms(a), _forms(b)) for a, b in _NONE.findall(text)]
    rules += [("some", a, b, _forms(a), _forms(b)) for a, b in _SOME.findall(text)]
    _QUESTION_WORDS = {"what", "why", "how", "who", "which", "when", "where",
                       "that", "this", "it", "there", "he", "she", "they", "i"}
    instances = [(a, b, _forms(a), _forms(b)) for a, b in _INSTANCE.findall(text)
                 if a.lower() not in _QUESTION_WORDS]
    queries = [(a, b, _forms(a), _forms(b)) for a, b in _QUERY.findall(text)]
    # A syllogism needs an explicit quantified premise or a stated logic task.
    # "What is a ghazal?" and "Why is the sky blue?" are ordinary questions,
    # not logical puzzles, and must go to the research pipeline.
    explicit_logic = bool(rules) or bool(re.search(
        r"\b(syllogism|premise|premises|given that|therefore|hence|deduce|deduction|"
        r"valid|invalid|conclusion|logically follows)\b", text, re.I))
    if not explicit_logic or (not rules and not instances):
        return None
    if not queries:
        if not re.search(r"\b(conclude|conclusion|follow|valid|true|therefore)\b", text, re.I):
            return None
        queries = [("?", "?", frozenset(), frozenset())]

    all_rules = [r for r in rules if r[0] == "all"]
    none_rules = [r for r in rules if r[0] == "none"]

    def categories(entity: frozenset) -> Tuple[List[frozenset], List[str]]:
        cats: List[frozenset] = [entity]  # treat the subject itself as a category
        trace: List[str] = []
        for a, b, ef, cf in instances:
            if ef & entity:
                if not any(cf & c for c in cats):
                    cats.append(cf)
                trace.append(f"{a} is given as a {b}.")
        grown = True
        while grown:
            grown = False
            for _kind, subj, pred, sf, pf in all_rules:
                if any(sf & c for c in cats) and not any(pf & c for c in cats):
                    cats.append(pf)
                    trace.append(f"All {subj} are {pred}, so the subject is also in {pred}.")
                    grown = True
        return cats, trace

    parts = []
    for ent, target, ef, tf in queries:
        if not ef:
            parts.append(_conclusion(rules, instances, depth))
            continue
        cats, trace = categories(ef)
        positive = any(tf & c for c in cats)
        contrad = any((sf & c and pf & tf) for _k, _a, _b, sf, pf in none_rules for c in cats)
        contrad = contrad or any((pf & c and sf & tf) for _k, _a, _b, sf, pf in none_rules for c in cats)
        if positive and not contrad:
            verdict, why = "Yes", f"I can derive {target} from the stated rules by forward chaining."
        elif contrad:
            verdict, why = "No", "A stated 'no' rule explicitly excludes that category."
        else:
            verdict, why = "Cannot be determined", (
                f"Nothing in the premises connects {ent} to {target}. The absence of a rule is "
                "not evidence of a negative.")
        parts.append(f"### Is {ent} a {target}?\n\n**{verdict}.** {why}\n\n" +
                     "\n".join(f"- {t}" for t in trace) if trace else
                     f"### Is {ent} a {target}?\n\n**{verdict}.** {why}\n\n"
                     "- I checked the category rules directly; no instantiation was given.")
    body = "\n\n".join(parts)
    short = "Each query below is answered from the stated premises only."
    out = ["## Logical reasoning", "", short, "", "## Premises as I read them", ""]
    for kind, subj, pred, _sf, _pf in rules:
        out.append(f"- {kind.upper()}: {subj} -> {pred}")
    for ent, cat, _ef, _cf in instances:
        out.append(f"- FACT: {ent} is a {cat}")
    out += ["", "## Analysis", "", body, "", "## Worked steps", "",
            "1. Translate every statement into (quantifier, subject, predicate).",
            "2. Instantiate the subject with any given individual.",
            "3. Apply 'all' rules repeatedly until no new category appears (forward chaining).",
            "4. Check 'no' rules for contradictions.",
            "5. If neither a proof nor a contradiction exists, answer 'cannot be determined'.",
            "", "## Common mistakes and limits", "",
            "- 'All A are B' does NOT imply 'all B are A' (the converse fallacy).",
            "- 'Some A are B' does not license a conclusion about an arbitrary individual.",
            "- 'No A are B' is symmetric, but 'all A are B' is not.",
            "- An undetermined conclusion is a correct answer, not a failure to answer."]
    if depth in ("deep", "exhaustive"):
        out += ["", "## Sources", "",
                "- Deterministic forward chaining in `ryzek_reason.py`; no external facts used.", "",
                "## What I could not verify", "",
                "I reason only from the premises you supplied. Whether those premises are true in "
                "the real world is a separate question."]
    out += ["", "## Keep going", "",
            "Add a premise, ask for the converse, or give me a truth-table style problem."]
    return "\n".join(out)


def _conclusion(rules, instances, depth: str) -> str:
    if not rules:
        return "No general rule was stated, so there is nothing to conclude beyond the given facts."
    lines = []
    for kind, subj, pred, _sf, _pf in rules:
        if kind == "all":
            lines.append(f"All {subj} are {pred}. Chaining with another 'all' rule extends this.")
        elif kind == "none":
            lines.append(f"No {subj} are {pred}; any {subj} is therefore excluded from {pred}.")
        else:
            lines.append(f"Some {subj} are {pred}; this does not generalise to every {subj}.")
    return "**What follows:**\n\n" + "\n".join(f"- {l}" for l in lines)


# ---------------------------------------------------------------------------
# Numeric operations, comparisons, word problems
# ---------------------------------------------------------------------------

_UNIT_FACTORS = {
    "mm": 0.001, "millimeter": 0.001, "millimetre": 0.001,
    "cm": 0.01, "centimeter": 0.01, "centimetre": 0.01,
    "m": 1.0, "meter": 1.0, "metre": 1.0,
    "km": 1000.0, "kilometer": 1000.0, "kilometre": 1000.0,
    "g": 0.001, "gram": 0.001,
    "kg": 1.0, "kilogram": 1.0,
    "mg": 0.000001, "milligram": 0.000001,
    "s": 1.0, "sec": 1.0, "second": 1.0, "seconds": 1.0,
    "min": 60.0, "minute": 60.0, "minutes": 60.0,
    "h": 3600.0, "hr": 3600.0, "hour": 3600.0, "hours": 3600.0,
}


def _comparison(text: str, depth: str) -> Optional[str]:
    if not re.search(r"\b(which|who|is|what)\b.*\b(bigger|larger|greater|smaller|less|more|"
                     r"heavier|lighter|faster|slower|higher|lower|largest|biggest|greatest|"
                     r"maximum|max|smallest|least|minimum|min)\b|\bcompare\s+\d", text, re.I):
        return None
    nums = _nums(text)
    if len(nums) < 2:
        return None
    if len(nums) > 2 and re.search(r"\b(largest|biggest|greatest|maximum|max|smallest|least|minimum|min)\b", text, re.I):
        want_max = bool(re.search(r"\b(largest|biggest|greatest|maximum|max)\b", text, re.I))
        val = max(nums) if want_max else min(nums)
        word = "largest" if want_max else "smallest"
        return _wrap("Comparison solved", f"The {word} value is **{_fmt(val)}**.",
                     [f"I read {len(nums)} values: {', '.join(_fmt(v) for v in nums)}.",
                      f"Compare every pair, keeping the running {word}.",
                      f"Result: {_fmt(val)}."],
                     ["Check that all values use the same unit.",
                      "Ties should be reported, not silently broken."],
                     depth, "All values are directly comparable numbers.")
    if len(nums) != 2:
        return None
    a, b = nums[0], nums[1]
    units = [u.lower() for u in re.findall(r"(?:" + NUM + r")\s*([a-zA-Z°]+)", text)
            if u.lower() in _UNIT_FACTORS]
    ua = units[0] if len(units) > 0 else ""
    ub = units[1] if len(units) > 1 else ua
    fa, fb = _UNIT_FACTORS.get(ua), _UNIT_FACTORS.get(ub)
    same_dimension = fa is not None and fb is not None
    if same_dimension:
        va, vb = a * fa, b * fb
        if abs(fa - fb) < 1e-12 and ((fa >= 60) != (fb >= 60)):
            same_dimension = False
    else:
        va, vb = a, b
        same_dimension = True  # both bare numbers
    if ua and ub and ua != ub and not (fa and fb):
        return _wrap("Comparison", "Those two quantities have different units, so I cannot rank them directly.",
                     [f"I read {_fmt(a)} {ua} and {_fmt(b)} {ub}.",
                      "Comparing length with mass, or seconds with metres, is undefined without a conversion."],
                     ["Convert to a common unit first.", "State what 'bigger' means for this quantity."],
                     depth, "A numerical comparison is meaningful only within one dimension.")
    if abs(va - vb) < 1e-12:
        verdict = f"**{_fmt(a)} {ua} and {_fmt(b)} {ub} are equal** after normalisation."
    else:
        hi = f"{_fmt(a)} {ua}" if va > vb else f"{_fmt(b)} {ub}"
        lo = f"{_fmt(b)} {ub}" if va > vb else f"{_fmt(a)} {ua}"
        verdict = f"**{hi.strip()} is greater** than {lo.strip()}.".replace("  ", " ")
    steps = [f"I read the two quantities as {_fmt(a)} {ua} and {_fmt(b)} {ub}.".strip() + ".",
             (f"Convert to a common base: {_fmt(a)} × {_fmt(fa)} = {_fmt(va)}; "
              f"{_fmt(b)} × {_fmt(fb)} = {_fmt(vb)}." if fa and fb else
              "Both values are plain numbers, so no conversion is needed."),
             f"Compare: {_fmt(va)} vs {_fmt(vb)}."]
    return _wrap("Comparison solved", verdict, steps,
                 ["Compare normalised values, never the raw numbers with different units.",
                  "Watch for 'less than' wording reversing the answer.",
                  "Equality needs a tolerance when the values come from measurements."],
                 depth, "Both numbers describe the same kind of quantity.")


def _numeric(text: str, depth: str) -> Optional[str]:
    low = text.lower()
    nums = _nums(text)

    m = re.search(r"\b(?:average|mean)\s+of\s+(.+)$", low)
    if m:
        vals = _nums(m.group(1))
        if len(vals) >= 2:
            total = sum(vals)
            avg = total / len(vals)
            return _wrap("Average", f"The mean is **{_fmt(avg)}**.",
                         [f"Values: {', '.join(_fmt(v) for v in vals)} ({len(vals)} values).",
                          f"Sum = {' + '.join(_fmt(v) for v in vals)} = {_fmt(total)}.",
                          f"Mean = {_fmt(total)} ÷ {len(vals)} = {_fmt(avg)}."],
                         ["The mean is not the median or the mode.",
                          "Outliers pull the mean strongly.",
                          "Divide by the count of values, not by the largest value."],
                         depth, "Arithmetic mean of the numbers listed.")

    m = re.search(r"\bmedian\s+of\s+(.+)$", low)
    if m:
        vals = sorted(_nums(m.group(1)))
        if len(vals) >= 2:
            n = len(vals)
            med = vals[n // 2] if n % 2 else (vals[n // 2 - 1] + vals[n // 2]) / 2
            return _wrap("Median", f"The median is **{_fmt(med)}**.",
                         [f"Sorted values: {', '.join(_fmt(v) for v in vals)}.",
                          f"There are {n} values; the middle is {'one value' if n % 2 else 'the average of the two middle values'}.",
                          f"Median = {_fmt(med)}."],
                         ["Sort the values before taking the middle.", "Even counts need the mean of the two central values."],
                         depth, "Median of the numbers listed.")

    m = re.search(r"\b(?:gcd|hcf|greatest common divisor)\s+of\s+(\d+)\s+(?:and|,)\s*(\d+)", low)
    if m:
        a, b = int(m.group(1)), int(m.group(2))
        g = math.gcd(a, b)
        return _wrap("Greatest common divisor", f"The GCD of {a} and {b} is **{g}**.",
                     [f"Euclid: gcd({a}, {b}) → gcd({b}, {a} % {b}) = gcd({b}, {a % b}).",
                      f"Continuing the reduction gives {g}.",
                      f"Check: {a}/{g} = {a // g}, {b}/{g} = {b // g}, which share no further factor."],
                     ["GCD is always positive.", "Do not confuse it with the LCM."],
                     depth, "Both inputs are non-negative integers.")

    m = re.search(r"\b(?:lcm|least common multiple)\s+of\s+(\d+)\s+(?:and|,)\s*(\d+)", low)
    if m:
        a, b = int(m.group(1)), int(m.group(2))
        g = math.gcd(a, b)
        lcm = abs(a * b) // g if g else 0
        return _wrap("Least common multiple", f"The LCM of {a} and {b} is **{lcm}**.",
                     [f"gcd({a}, {b}) = {g}.", f"lcm = |{a} × {b}| ÷ {g} = {lcm}.",
                      f"Check: {lcm}/{a} = {lcm // a if a else 0}, {lcm}/{b} = {lcm // b if b else 0}."],
                     ["Use the product divided by the GCD, not the product itself.",
                      "This only applies to integers."], depth)

    m = re.search(r"\bis\s+(\d+)\s+(?:a\s+)?prime\b", low)
    if m:
        n = int(m.group(1))
        if n < 2:
            answer, why = "No", f"{n} is less than 2, and primes are integers greater than 1."
        else:
            div = next((d for d in range(2, int(math.isqrt(n)) + 1) if n % d == 0), None)
            answer = "No" if div else "Yes"
            why = (f"{n} = {div} × {n // div}, so it is composite." if div else
                   f"No divisor up to √{n} ≈ {math.isqrt(n)} divides {n}.")
        return _wrap("Primality", f"**{answer}**, {n} is {'prime' if answer == 'Yes' else 'not prime'}.",
                     [f"Test {n}.", f"Check divisors from 2 to √{n} = {math.isqrt(n)}.", why],
                     ["1 is not prime.", "Only test up to the square root, not up to n.",
                      "2 is the only even prime."], depth)

    m = re.search(r"\b(?:factorial\s+of\s+(\d+)|(\d+)\s*!)", low)
    if m:
        n = int(m.group(1) or m.group(2))
        if 0 <= n <= 20:
            val = math.factorial(n)
            return _wrap("Factorial", f"{n}! = **{val}**.",
                         [f"{n}! = {' × '.join(str(i) for i in range(1, n + 1)) or '1'}.",
                          f"Multiplying through gives {val}.",
                          "By definition 0! = 1." if n == 0 else "Factorial grows very quickly."],
                         ["0! = 1, not 0.", "Factorial is defined for non-negative integers."], depth)

    m = re.search(r"\b(?:sum|total)\s+of\s+(?:the\s+)?(?:first\s+)?(?:numbers?|integers?)\s+(?:from\s+1\s+to|1\s+to|up\s+to)\s+(\d+)", low)
    if m:
        n = int(m.group(1))
        val = n * (n + 1) // 2
        return _wrap("Sum of a series", f"The sum 1 + 2 + … + {n} is **{val}**.",
                     [f"Use the triangular-number formula n(n+1)/2.",
                      f"n = {n}: {n} × {n + 1} / 2 = {val}.",
                      f"Pairing terms (1+{n}, 2+{n-1}, …) gives the same result."],
                     ["The formula assumes consecutive integers starting at 1.",
                      "Check n is a positive integer."], depth)

    m = re.search(r"\bwhat\s+(?:percent|percentage)\s+is\s+" + NUM + r"\s+of\s+" + NUM, low)
    if m:
        a, b = _nums(m.group(0))[:2]
        pct = (a / b * 100) if b else 0
        return _wrap("Percentage", f"{_fmt(a)} is **{_fmt(round(pct, 4))}%** of {_fmt(b)}.",
                     [f"Divide the part by the whole: {_fmt(a)} ÷ {_fmt(b)} = {_fmt(round(a / b, 6)) if b else 'undefined'}.",
                      f"Multiply by 100 to convert to a percentage: {_fmt(round(pct, 4))}%."],
                     ["Identify which number is the whole.", "A zero whole makes the percentage undefined."], depth)

    m = re.search(r"\bsimplif(?:y|ied)?\s+(?:the\s+)?ratio\s+(\d+)\s*(?::|to)\s*(\d+)", low)
    if m:
        a, b = int(m.group(1)), int(m.group(2))
        g = math.gcd(a, b) or 1
        return _wrap("Ratio", f"The ratio {a}:{b} simplifies to **{a // g}:{b // g}**.",
                     [f"Find gcd({a}, {b}) = {g}.", f"Divide both terms: {a // g} and {b // g}."],
                     ["Both terms must be integers.", "Order matters in a ratio."], depth)

    # simple word problems with two numbers
    if len(nums) >= 2:
        a, b = nums[0], nums[1]
        if re.search(r"\b(give away|gave away|lose|lost|spend|spent|remove|removed|eat|ate|used up|left|remain|remaining)\b", low) and \
           re.search(r"\b(have|had|start|started|left|remain|remaining|how many)\b", low):
            val = a - b
            return _wrap("Word problem", f"**{_fmt(val)}** remain.",
                         [f"Starting amount: {_fmt(a)}.", f"Amount removed: {_fmt(b)}.",
                          f"Remaining = {_fmt(a)} − {_fmt(b)} = {_fmt(val)}."],
                         ["Check which number is the starting amount.",
                          "If the removed amount exceeds the start, the result is negative."],
                         depth, "The first number is the starting amount and the second is removed.")
        if re.search(r"\b(shared|split|divide|divided|distributed)\b.*\b(among|between|into)\b|\b(each|per person)\b", low):
            if b:
                return _wrap("Word problem", f"Each share is **{_fmt(a / b)}**.",
                             [f"Total: {_fmt(a)}.", f"Number of shares: {_fmt(b)}.",
                              f"Each = {_fmt(a)} ÷ {_fmt(b)} = {_fmt(a / b)}."],
                             ["Division by zero is undefined.", "Check whether the result should be rounded to whole items."],
                             depth, "The total is shared equally.")
        m = re.search(NUM + r"\s*(km|kilometers?|kilometres?|m|meters?|metres?|miles?)\s+in\s+" +
                      NUM + r"\s*(hours?|hrs?|h|minutes?|mins?|min|seconds?|secs?|s)\b", low)
        if m:
            d, t = _nums(m.group(0))[:2]
            unit = re.findall(r"(km|kilometers?|kilometres?|m|meters?|metres?|miles?)", m.group(0))[0]
            tu = re.findall(r"(hours?|hrs?|h|minutes?|mins?|min|seconds?|secs?|s)", m.group(0))[0]
            tf = 1.0 if tu.startswith(("hour", "hr", "h")) else (1 / 60 if tu.startswith(("min", "minute")) else 1 / 3600)
            speed = d / (t * tf) if t else 0
            return _wrap("Speed", f"The average speed is **{_fmt(round(speed, 4))} {unit} per hour**.",
                         [f"Distance = {_fmt(d)} {unit}.", f"Time = {_fmt(t)} {tu} = {_fmt(t * tf)} hours.",
                          f"Speed = distance ÷ time = {_fmt(round(speed, 4))} {unit}/h."],
                         ["Average speed is not instantaneous speed.", "Convert time to hours before dividing."], depth)
    return None


# ---------------------------------------------------------------------------
# Analytical / decision frameworks
# ---------------------------------------------------------------------------


def _analytical(text: str, depth: str) -> Optional[str]:
    low = text.lower()
    if not re.search(r"\b(should i|which (?:is|should|one)|compare|comparison|pros and cons|"
                     r"trade.?off|analyse|analyze|evaluate|weigh up|decide between|"
                     r"analytical reasoning|cost.?benefit)\b", low):
        return None
    # "which is bigger 3 or 5" is handled by _comparison instead
    if _nums(text) and re.search(r"\b(bigger|greater|larger|smaller|heavier|lighter|largest|"
                                r"biggest|greatest|maximum|max|smallest|least|minimum|min)\b", low):
        return None
    m = re.search(r"\b(?:should i|decide between|compare|comparison of|pros and cons of|"
                  r"evaluate|analyse|analyze)\s+(.+?)(?:\?|$|,\s*please)", text, re.I)
    subject = (m.group(1).strip() if m else text.strip().rstrip("?."))[:160]
    short = ("Here is a complete decision framework for **" + subject +
             "**. I will not invent facts about the options; I will show you exactly how to reach "
             "a defensible answer.")
    out = ["## Analytical reasoning", "", short, "",
           "## 1. Define the decision", "",
           f"- **Question:** {subject}.",
           "- **Decision-maker:** you; **horizon:** short-term and long-term.",
           "- **Success criterion:** what would have to be true for you to call this the right call?",
           "", "## 2. List the criteria", "",
           "1. **Benefit** - what do you gain, and how large is it?",
           "2. **Cost** - money, time, attention and opportunity cost.",
           "3. **Risk** - how likely is a bad outcome, and how bad would it be?",
           "4. **Reversibility** - can you undo the decision cheaply?",
           "5. **Evidence quality** - is each claim measured, sourced or assumed?",
           "6. **Fit** - does it match your actual constraints and values?",
           "", "## 3. Score it", "",
           "Build a small table: give each criterion a weight from 1 to 5, score each option from "
           "1 to 5, and multiply. The weighted totals are not the answer - they are a way to expose "
           "which assumption is doing the work.", "",
           "## 4. Test the reasoning", "",
           "- **Sensitivity:** change the weight of the most important criterion. Does the winner change?",
           "- **Reversal:** try to argue for the option you currently dislike.",
           "- **Base rate:** what usually happens to people in this situation?",
           "- **Pre-mortem:** imagine it failed in a year; write down the most likely reason.",
           "", "## 5. Decide", "",
           "- If the downside is small and reversible, choose quickly and gather feedback.",
           "- If the downside is large and hard to reverse, get one more independent data point first.",
           "- If two options stay tied, pick the one that preserves more future options.",
           "", "## Common mistakes and limits", "",
           "- Deciding before naming the criteria, then rationalising afterwards.",
           "- Treating a confident opinion as evidence.",
           "- Ignoring opportunity cost: the real price is the best alternative you gave up.",
           "- Averaging away a single fatal risk instead of treating it as a veto."]
    if depth in ("deep", "exhaustive"):
        out += ["", "## A small Python scorer", "",
                "```python\n"
                "criteria = {'benefit': 5, 'cost': 4, 'risk': 5, 'reversibility': 3}\n"
                "options = {\n"
                "    'A': {'benefit': 4, 'cost': 2, 'risk': 4, 'reversibility': 5},\n"
                "    'B': {'benefit': 3, 'cost': 4, 'risk': 2, 'reversibility': 2},\n"
                "}\n"
                "totals = {name: sum(criteria[k] * scores[k] for k in criteria)\n"
                "          for name, scores in options.items()}\n"
                "print(totals)  # change the weights and see if the ranking flips\n"
                "```", "",
                "## Sources", "",
                "- Structured decision analysis in `ryzek_reason.py` - no external claims about "
                "the specific options.", "",
                "## What I could not verify", "",
                "I do not have your costs, constraints or preferences. Give me the two or three "
                "real options and the criteria that matter to you, and I will fill in the table "
                "with a concrete, reasoned recommendation instead of a template."]
    out += ["", "## Keep going", "",
            "Tell me the actual options and your constraints and I will produce the scored "
            "comparison and a recommendation."]
    return "\n".join(out)


# ---------------------------------------------------------------------------
# Small riddle bank (tone / basic response capability)
# ---------------------------------------------------------------------------

RIDDLES = [
    (r"keys but no locks|keys but can't open", "A piano", "A piano has keys that produce notes, not keys that open doors."),
    (r"has a face but no eyes|has hands but no arms", "A clock", "A clock has a face and hands, but neither eyes nor arms."),
    (r"speaks without a mouth|repeats.*without speaking", "An echo", "An echo returns your own sound without a voice of its own."),
    (r"follows you.*but.*never.*catch|grows.*light.*shrinks.*dark", "Your shadow", "A shadow tracks you but cannot be grasped, and it depends entirely on light."),
    (r"gets shorter.*the more.*use|taller.*when.*young", "A candle", "A candle shrinks as it burns."),
    (r"can travel.*around.*world.*stay.*corner", "A stamp", "A stamp travels on letters while sitting in the corner of an envelope."),
    (r"has cities but no houses|has rivers but no water|has roads but no cars", "A map", "A map represents places without containing the physical things themselves."),
]


def _riddle(text: str, depth: str) -> Optional[str]:
    low = text.lower()
    for pattern, answer, why in RIDDLES:
        if re.search(pattern, low, re.I):
            return _wrap("Riddle", f"The answer is **{answer}**.",
                         [f"Clue: {why}", "Check every part of the wording against the answer.",
                          "Riddles usually turn on a word with two meanings (keys, face, hands)."],
                         ["The obvious literal reading is usually the trap.",
                          "If a clue does not fit, the answer is wrong - do not force it."],
                         depth, "The wording is a classic wordplay riddle.",
                         "This is a wordplay puzzle. The trick is that ordinary words such as "
                         "'keys', 'face' or 'hands' are being used in a second sense.")
    return None


def solve(text: str, depth: str = "deep") -> Optional[str]:
    """Return a reasoned answer, or None if the question needs research."""
    if not text or len(text.strip()) < 3:
        return None
    for fn in (_sequence, _ordering, _syllogism, _comparison, _numeric,
               _riddle, _analytical):
        try:
            out = fn(text, depth)
        except Exception:
            out = None
        if out:
            return out
    return None
