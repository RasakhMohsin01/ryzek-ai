#!/usr/bin/env python3
"""
Ryzek AI - actual writing, not a description of writing.

When someone says "write a Python function that reverses a string", "write an
email to my teacher asking for leave", "write an essay on climate change" or
"write a letter to my friend", Ryzek produces the finished piece at the top of
its answer: runnable code, a copy-ready email, a real essay, a formatted letter,
a story, a poem, a speech, an article or a report.

Nothing here claims to know facts the user did not supply. Where a specific
detail is needed (a date, a name, a number) an explicit [placeholder] is used
and listed in the notes, so the piece is honest as well as usable.
"""

from __future__ import annotations

import re
from typing import Dict, List, Optional, Tuple

import ryzek_urdu

# ---------------------------------------------------------------------------
# Detection
# ---------------------------------------------------------------------------

WRITE_RE = re.compile(
    r"\b(?:write|draft|compose|create|make|generate|produce|give me|show me|"
    r"type|pen|build|prepare|summarise|summarize|draft up|put together)\b", re.I)
BLOCK_RE = re.compile(r"^\s*(?:explain|what is|what are|define|why does|why is|how does)\b", re.I)

# Urdu poetry is its own writing genre. Roman-Urdu and Arabic-script requests,
# plus "ghazal / nazm / shayari", all land here instead of becoming a research
# answer about what a ghazal is.
URDU_RE = re.compile(
    r"\burdu\b|\burdou\b|\bshayari\b|\bshaayari\b|\bnazm\b|\bghazal\b|"
    r"\blikh(?:o|iye|do|na)?\b|[\u0600-\u06ff]", re.I)
URDU_START = re.compile(r"^\s*(?:urdu|urdou|ghazal|shayari|shaayari|nazm|likh|likho|likhiye|[\u0600-\u06ff])", re.I)

# Specific real-world document types, checked before the generic genres.
SPECIAL: List[Tuple[str, str, str, str]] = [
    (r"\b(?:leave application|application for leave|leave letter)\b", "letter", "requesting leave", "formal"),
    (r"\b(?:cover letter|job application letter)\b", "letter", "applying for a position", "formal"),
    (r"\b(?:resignation letter|letter of resignation)\b", "letter", "resigning from a position", "formal"),
    (r"\b(?:recommendation letter|letter of recommendation)\b", "letter", "recommending someone", "formal"),
    (r"\b(?:condolence|sympathy letter)\b", "letter", "expressing sympathy", "formal"),
    (r"\b(?:complaint email|email of complaint|complaint)\b", "email", "raising a concern", "formal"),
    (r"\b(?:apology email|apology letter|apologise|apologize|say sorry)\b", "email", "apologising", "friendly"),
    (r"\b(?:invitation email|invitation letter|invite|invitation)\b", "email", "inviting someone", "friendly"),
    (r"\b(?:thank.?you note|thank you email|thank you letter)\b", "email", "expressing thanks", "friendly"),
    (r"\b(?:proposal|project proposal)\b", "report", "proposing a course of action", "formal"),
    (r"\b(?:formal notice|circular|notice)\b", "letter", "giving formal notice", "formal"),
]

GENRES: List[Tuple[str, str]] = [
    (r"\b(?:e-?mail|mail)\b", "email"),
    (r"\b(?:python|function|script|program|code|method|algorithm|def )\b", "code"),
    (r"\b(?:essay|composition|term paper)\b", "essay"),
    (r"\b(?:letter)\b", "letter"),
    (r"\b(?:short story|story|tale)\b", "story"),
    (r"\b(?:poem|poetry|verse|sonnet|ghazal)\b", "poem"),
    (r"\b(?:speech|talk|address)\b", "speech"),
    (r"\b(?:article|blog post|blog)\b", "article"),
    (r"\b(?:report|summary|overview)\b", "report"),
    (r"\b(?:note|message|text|caption)\b", "note"),
]

_GENRE_WORDS = (
    r"e-?mail|mail|essay|composition|term paper|letter|python|function|script|"
    r"program|code|method|algorithm|short story|story|tale|poem|poetry|verse|"
    r"sonnet|ghazal|speech|talk|address|article|blog post|blog|report|summary|"
    r"overview|note|message|text|caption|urdu poetry|urdu|ghazal|shayari|nazm|leave application|cover letter|"
    r"complaint|invitation|apology|proposal|notice"
)


def detect(text: str) -> Optional[Dict[str, str]]:
    """Return genre/tone/purpose metadata, or None if this is not a writing task."""
    t = (text or "").strip()
    if len(t) < 7 or BLOCK_RE.match(t):
        return None
    if not WRITE_RE.search(t) and not re.match(
            r"^\s*(?:e-?mail|essay|letter|story|poem|speech|article|report|note|"
            r"python function|python script|function|script|code|def )\b", t, re.I) \
            and not URDU_START.match(t):
        return None
    low = t.lower()
    genre = purpose_hint = tone_hint = ""
    # Urdu poetry first: "write urdu poetry", "type a ghazal", "ایک غزل لکھ دو".
    if URDU_RE.search(t) and (WRITE_RE.search(t) or URDU_START.match(t)):
        meta = _parse(t, "urdu_poem", "", "")
        meta["genre"] = "urdu_poem"
        return meta
    for pattern, g, purpose, tone in SPECIAL:
        if re.search(pattern, low, re.I):
            genre, purpose_hint, tone_hint = g, purpose, tone
            break
    if not genre:
        for pattern, g in GENRES:
            if re.search(pattern, low, re.I):
                genre = g
                break
    if not genre:
        return None

    # An explicitly named document type wins over the subtype guess.
    if re.search(r"\b(e-?mail|mail)\b", low) and not re.search(r"\bletter\b", low):
        genre = "email"
    elif re.search(r"\bletter\b", low):
        genre = "letter"
    if re.search(r"\b(python|function|script|program)\b", low):
        genre = "code"

    meta = _parse(t, genre, purpose_hint, tone_hint)
    meta["genre"] = genre
    return meta


def _parse(t: str, genre: str, purpose_hint: str, tone_hint: str) -> Dict[str, str]:
    # Recipient
    recipient = ""
    if genre in ("email", "letter", "note"):
        m = re.search(r"\bto\s+(my\s+[A-Za-z]+|the\s+[A-Za-z]+(?:\s+[A-Za-z]+)?|"
                      r"Mr\.?\s+[A-Za-z]+|Ms\.?\s+[A-Za-z]+|Mrs\.?\s+[A-Za-z]+|"
                      r"Dr\.?\s+[A-Za-z]+|Sir|Madam|[A-Z][a-z]{2,}(?:\s+[A-Z][a-z]{2,})?)", t)
        if m:
            recipient = m.group(1).strip()

    work = re.sub(r"\s+", " ", t).strip().rstrip(".!?")
    work = re.sub(r"^\s*(?:hi|hey|hello|good morning|good afternoon|good evening|"
                  r"salam|yo|dear)\s*[,!:-]?\s*", "", work, flags=re.I)
    if recipient:
        work = re.sub(re.escape(recipient), " ", work, count=1, flags=re.I)
    work = re.sub(r"^\s*(?:please|plz|kindly)\s+", "", work, flags=re.I)
    work = re.sub(r"^\s*(?:can you|could you|would you|will you)\s+", "", work, flags=re.I)
    work = re.sub(r"^\s*(?:write|draft|compose|create|make|generate|produce|give me|"
                  r"show me|type|pen|build|prepare|summarise|summarize|put together|draft up)\s+",
                  "", work, flags=re.I)
    work = re.sub(r"^\s*(?:me\s+)?(?:a|an|the|some)\s+", "", work, flags=re.I)
    for _ in range(3):
        work = re.sub(r"^\s*(?:simple|short|long|detailed|formal|informal|friendly|"
                      r"professional|polite|nice|good|quick|small|little|brief|new)\s+",
                      "", work, flags=re.I)
    for _ in range(4):
        new = re.sub(r"^\s*(?:" + _GENRE_WORDS + r")\b\s*", "", work, flags=re.I)
        if new == work:
            break
        work = new
    work = re.sub(r"^\s*(?:in|using|with)\s+(?:python|simple python)\b\s*", "", work, flags=re.I)
    for _ in range(4):
        new = re.sub(r"^\s*(?:on|about|regarding|concerning|of|that|which|for|to|please|"
                     r"asking|requesting|my|please)\b\s*", "", work, flags=re.I)
        if new == work:
            break
        work = new
    work = re.sub(r"\s+", " ", work).strip(" ,;:-")

    topic = work[:140].strip()
    if not topic:
        topic = "the matter we discussed"
    purpose = purpose_hint or (topic if len(topic) < 60 else "the matter described below")

    _PHRASES = {
        "requesting leave": "to request leave",
        "applying for a position": "to apply for the position",
        "resigning from a position": "to submit my resignation",
        "recommending someone": "to offer a recommendation",
        "expressing sympathy": "to express my condolences",
        "raising a concern": "to raise a concern",
        "apologising": "to apologise",
        "inviting someone": "to invite you",
        "expressing thanks": "to thank you",
        "proposing a course of action": "to propose a course of action",
        "giving formal notice": "to give formal notice",
    }
    if purpose_hint:
        purpose_phrase = _PHRASES.get(purpose_hint, f"about {purpose_hint}")
    elif re.search(r"\b(?:asking|request|apply|leave|extension|permission)\b", t, re.I):
        purpose_phrase = f"to request {topic}"
    else:
        purpose_phrase = f"about {topic}"

    tone = tone_hint
    if re.search(r"\b(formal|official|professional|polite|respectful)\b", t, re.I):
        tone = "formal"
    elif re.search(r"\b(casual|informal|friendly|funny|warm)\b", t, re.I) or \
            re.search(r"\bmy (?:friend|mum|mom|dad|brother|sister|cousin)\b", t, re.I):
        tone = "friendly"
    if not tone:
        tone = "formal" if (genre in ("essay", "report", "article", "speech") or
                           re.search(r"teacher|manager|principal|boss|sir|madam|company|"
                                     r"university|client|officer|director", t, re.I)) else "friendly"

    length = "short" if re.search(r"\b(short|brief|quick|small|little)\b", t, re.I) else "long"
    return {"topic": topic, "recipient": recipient, "purpose": purpose,
            "purpose_phrase": purpose_phrase, "tone": tone, "length": length, "raw": t}


# ---------------------------------------------------------------------------
# Small helpers
# ---------------------------------------------------------------------------


def _cap(s: str) -> str:
    s = (s or "").strip()
    return s[:1].upper() + s[1:] if s else "The subject"


def _salutation(recipient: str, tone: str) -> str:
    if not recipient:
        return "Dear Sir/Madam," if tone == "formal" else "Hi there,"
    r = recipient.strip()
    if r.lower().startswith("my "):
        r = r[3:].strip()
        return (f"Dear {r.title()}," if tone == "formal" else f"Hi {r},")
    if r.lower().startswith("the "):
        return f"Dear {r[4:].strip().title()},"
    return f"Dear {r},"


def _recipient_display(recipient: str) -> str:
    if not recipient:
        return "Sir/Madam"
    r = recipient.strip()
    if r.lower().startswith("my "):
        return r[3:].strip().title()
    if r.lower().startswith("the "):
        return "The " + r[4:].strip().title()
    return r


def _signoff(tone: str) -> str:
    return "Yours sincerely," if tone == "formal" else "Warm regards,"


def _fence(body: str, lang: str = "text") -> str:
    return "```" + lang + "\n" + body.strip() + "\n```"


def _finish(piece: str, meta: Dict[str, str], depth: str,
            adapt: List[str], why: List[str], checklist: List[str],
            extra: str = "", title: str = "") -> str:
    out = [f"## {title or (_cap(meta['genre']) + ' ready to use')}", "", piece.strip()]
    if depth == "quick":
        return "\n".join(out)
    out += ["", "## How to adapt it", ""] + [f"- {x}" for x in adapt]
    if depth in ("deep", "exhaustive"):
        out += ["", "## Why it is written this way", ""] + [f"- {x}" for x in why]
        out += ["", "## Before you send it / hand it in", ""] + [f"- {x}" for x in checklist]
    if depth == "exhaustive":
        out += ["", "## More detail", "", extra or
                "Change one thing at a time - the reader, the tone or the length - and read "
                "the result aloud before you use it.", "",
                "## Quick check", "",
                "- Replace every [placeholder] with a real name, date or number.",
                "- Keep one audience and one tone throughout.",
                "- Say clearly what should happen next.", "",
                "I used [placeholders] because I do not know your real names or dates. "
                "I have not invented any of them."]
    out += ["", "## Keep going", "",
            "Tell me the names, dates or tone and I will rewrite it for you."]
    return "\n".join(out)


# ---------------------------------------------------------------------------
# Python code
# ---------------------------------------------------------------------------

CODE_LIBRARY: List[Tuple[str, str, str, str]] = [
    (r"revers\w*\s+(?:a\s+)?(?:string|text|word)|reverse\s+string|reverse\s+a\s+word",
     "Reverse a string",
     '''def reverse_string(text: str) -> str:
    """Return `text` backwards, leaving the original unchanged."""
    return text[::-1]


if __name__ == "__main__":
    assert reverse_string("Ryzek") == "zekyR"
    assert reverse_string("") == ""
    assert reverse_string("a") == "a"
    print(reverse_string("Python"))   # nohtyP''',
     "Slicing with a step of -1 walks the string from the last character to the first."),

    (r"palindrom", "Check whether a string is a palindrome",
     '''def is_palindrome(text: str) -> bool:
    """True if `text` reads the same forwards and backwards, ignoring case and spaces."""
    cleaned = "".join(ch.lower() for ch in text if ch.isalnum())
    return cleaned == cleaned[::-1]


if __name__ == "__main__":
    assert is_palindrome("A man, a plan, a canal: Panama")
    assert not is_palindrome("Ryzek")
    print(is_palindrome("level"))     # True''',
     "Normalising the input first is what makes punctuation and capital letters harmless."),

    (r"factorial", "Factorial of a number",
     '''def factorial(n: int) -> int:
    """Return n! for a non-negative integer, computed iteratively."""
    if not isinstance(n, int) or n < 0:
        raise ValueError("n must be a non-negative integer")
    result = 1
    for i in range(2, n + 1):
        result *= i
    return result


if __name__ == "__main__":
    assert factorial(0) == 1
    assert factorial(5) == 120
    print(factorial(6))               # 720''',
     "An iterative loop avoids recursion limits and makes the base case 0! = 1 explicit."),

    (r"fibonacci|fib\b", "Fibonacci numbers",
     '''def fibonacci(n: int) -> int:
    """Return the n-th Fibonacci number (fib(0)=0, fib(1)=1)."""
    if not isinstance(n, int) or n < 0:
        raise ValueError("n must be a non-negative integer")
    a, b = 0, 1
    for _ in range(n):
        a, b = b, a + b
    return a


def fibonacci_sequence(count: int) -> list[int]:
    """Return the first `count` Fibonacci numbers."""
    if count < 0:
        raise ValueError("count must be non-negative")
    return [fibonacci(i) for i in range(count)]


if __name__ == "__main__":
    assert fibonacci(10) == 55
    assert fibonacci_sequence(8) == [0, 1, 1, 2, 3, 5, 8, 13]
    print(fibonacci_sequence(10))''',
     "Tuple assignment updates both terms at once, so no temporary variable is needed."),

    (r"prime|primality", "Test whether a number is prime",
     '''def is_prime(n: int) -> bool:
    """Return True if n is prime. Tests divisors only up to sqrt(n)."""
    if not isinstance(n, int) or n < 2:
        return False
    if n == 2:
        return True
    if n % 2 == 0:
        return False
    for d in range(3, int(n ** 0.5) + 1, 2):
        if n % d == 0:
            return False
    return True


if __name__ == "__main__":
    assert is_prime(97)
    assert not is_prime(1)
    assert not is_prime(91)
    print([n for n in range(30) if is_prime(n)])''',
     "Any composite number has a factor no larger than its square root, so testing beyond that is wasted work."),

    (r"gcd|greatest common divisor|hcf", "Greatest common divisor",
     '''def gcd(a: int, b: int) -> int:
    """Return the greatest common divisor using Euclid's algorithm."""
    a, b = abs(a), abs(b)
    while b:
        a, b = b, a % b
    return a


if __name__ == "__main__":
    assert gcd(48, 18) == 6
    assert gcd(7, 13) == 1
    print(gcd(270, 192))              # 6''',
     "Euclid's algorithm replaces the larger problem with a smaller one on every iteration."),

    (r"average|mean|arithmetic mean", "Average of a list of numbers",
     '''def average(values: list[float]) -> float:
    """Return the arithmetic mean of a non-empty list of numbers."""
    if not values:
        raise ValueError("values must not be empty")
    return sum(values) / len(values)


if __name__ == "__main__":
    assert average([4, 8, 15, 16, 23, 42]) == 18.0
    assert average([10]) == 10.0
    print(average([1, 2, 3, 4]))     # 2.5''',
     "The empty list is rejected explicitly so a ZeroDivisionError never surfaces later."),

    (r"sum\s+of|add\s+up|total\s+of", "Sum a list of numbers",
     '''def total(values: list[float]) -> float:
    """Return the sum of a list, treating an empty list as zero."""
    return sum(values)


if __name__ == "__main__":
    assert total([1, 2, 3]) == 6
    assert total([]) == 0
    print(total(range(1, 11)))        # 55''',
     "Python's built-in sum is implemented in C and is both clearer and faster than a manual loop."),

    (r"count\s+(?:the\s+)?vowels|vowel", "Count vowels in a string",
     '''def count_vowels(text: str) -> int:
    """Count vowels (a, e, i, o, u) in `text`, case-insensitively."""
    return sum(1 for ch in text.lower() if ch in "aeiou")


if __name__ == "__main__":
    assert count_vowels("Ryzek AI") == 3
    assert count_vowels("rhythm") == 0
    print(count_vowels("Beautiful"))''',
     "A generator expression avoids building an intermediate list."),

    (r"word count|count words|count\s+(?:the\s+)?words", "Count words in a sentence",
     '''def word_count(text: str) -> int:
    """Return the number of whitespace-separated words in `text`."""
    return len(text.split())


if __name__ == "__main__":
    assert word_count("Ryzek AI answers everything") == 4
    assert word_count("   ") == 0
    print(word_count("Hello, world!"))  # 2''',
     "str.split() with no argument collapses runs of whitespace automatically."),

    (r"fizz.?buzz", "FizzBuzz",
     '''def fizzbuzz(n: int) -> list[str]:
    """Return the FizzBuzz sequence from 1 to n inclusive."""
    out = []
    for i in range(1, n + 1):
        if i % 15 == 0:
            out.append("FizzBuzz")
        elif i % 3 == 0:
            out.append("Fizz")
        elif i % 5 == 0:
            out.append("Buzz")
        else:
            out.append(str(i))
    return out


if __name__ == "__main__":
    assert fizzbuzz(5) == ["1", "2", "Fizz", "4", "Buzz"]
    print(", ".join(fizzbuzz(15)))''',
     "The divisible-by-15 case must come first because it also satisfies the 3 and 5 cases."),

    (r"remove duplicates|unique|deduplicat|distinct", "Remove duplicates while keeping order",
     '''def unique(items: list) -> list:
    """Return `items` with duplicates removed, preserving first-seen order."""
    return list(dict.fromkeys(items))


if __name__ == "__main__":
    assert unique([3, 1, 3, 2, 1]) == [3, 1, 2]
    assert unique([]) == []
    print(unique(["a", "b", "a"]))''',
     "Dictionaries preserve insertion order in modern Python, so this is both short and stable."),

    (r"maximum|minimum|largest|smallest|max\s+and\s+min", "Find the largest and smallest values",
     '''def extremes(values: list[float]) -> tuple[float, float]:
    """Return (smallest, largest) for a non-empty list of numbers."""
    if not values:
        raise ValueError("values must not be empty")
    return min(values), max(values)


if __name__ == "__main__":
    assert extremes([3, 19, 7, 12]) == (3, 19)
    print(extremes([2.5, -1, 8]))''',
     "Two passes over the data is fine for small lists; one pass is better for very large ones."),

    (r"celsius|fahrenheit|temperature|convert.*degrees", "Convert Celsius to Fahrenheit",
     '''def celsius_to_fahrenheit(c: float) -> float:
    """Convert a Celsius temperature to Fahrenheit."""
    return c * 9 / 5 + 32


def fahrenheit_to_celsius(f: float) -> float:
    """Convert a Fahrenheit temperature to Celsius."""
    return (f - 32) * 5 / 9


if __name__ == "__main__":
    assert celsius_to_fahrenheit(100) == 212.0
    assert fahrenheit_to_celsius(32) == 0.0
    print(round(celsius_to_fahrenheit(37), 1))''',
     "This is an affine transform (scale then shift), not a plain multiplication."),

    (r"even\s+(?:or\s+)?odd|odd\s+or\s+even", "Check even or odd",
     '''def is_even(n: int) -> bool:
    """Return True if `n` is even."""
    return n % 2 == 0


def even_or_odd(n: int) -> str:
    """Return the words 'even' or 'odd' for an integer."""
    return "even" if is_even(n) else "odd"


if __name__ == "__main__":
    assert is_even(4) and not is_even(7)
    assert even_or_odd(0) == "even"
    print(even_or_odd(11))''',
     "The modulo operator gives the remainder, which is exactly the even/odd test."),

    (r"anagram", "Check whether two words are anagrams",
     '''from collections import Counter


def is_anagram(a: str, b: str) -> bool:
    """True if `a` and `b` contain the same letters with the same frequencies."""
    norm = lambda s: "".join(ch.lower() for ch in s if ch.isalnum())
    return Counter(norm(a)) == Counter(norm(b))


if __name__ == "__main__":
    assert is_anagram("listen", "silent")
    assert not is_anagram("Ryzek", "Python")
    print(is_anagram("Dormitory", "dirty room"))''',
     "Comparing letter counts is O(n) and correctly handles repeated letters."),

    (r"binary search", "Binary search in a sorted list",
     '''def binary_search(items: list, target) -> int:
    """Return the index of `target` in a sorted list, or -1 if absent."""
    lo, hi = 0, len(items) - 1
    while lo <= hi:
        mid = (lo + hi) // 2
        if items[mid] == target:
            return mid
        if items[mid] < target:
            lo = mid + 1
        else:
            hi = mid - 1
    return -1


if __name__ == "__main__":
    data = [1, 3, 5, 7, 9, 11]
    assert binary_search(data, 7) == 3
    assert binary_search(data, 4) == -1
    print(binary_search(data, 11))''',
     "Each step halves the search space, giving O(log n) time - but the list must already be sorted."),

    (r"bubble sort|sort a list|sorting", "Sort a list (and show how a simple sort works)",
     '''def sort_numbers(values: list[float]) -> list[float]:
    """Return a new sorted list; the input is left untouched."""
    return sorted(values)


def bubble_sort(values: list) -> list:
    """Teaching implementation of bubble sort. Returns a new list."""
    a = list(values)
    for end in range(len(a) - 1, 0, -1):
        for i in range(end):
            if a[i] > a[i + 1]:
                a[i], a[i + 1] = a[i + 1], a[i]
    return a


if __name__ == "__main__":
    assert sort_numbers([3, 1, 2]) == [1, 2, 3]
    assert bubble_sort([3, 1, 2]) == [1, 2, 3]
    print(sort_numbers([10, -5, 0, 7]))''',
     "Use sorted() in real code (Timsort, O(n log n)); bubble sort is included to show the mechanism."),

    (r"word frequency|frequency|count occurrences|count how many times", "Count word frequencies",
     '''from collections import Counter


def word_frequencies(text: str) -> dict[str, int]:
    """Return a mapping of word -> count, ignoring case and punctuation."""
    words = "".join(ch.lower() if ch.isalnum() else " " for ch in text).split()
    return dict(Counter(words))


if __name__ == "__main__":
    counts = word_frequencies("Ryzek answers Ryzek questions")
    assert counts["ryzek"] == 2
    print(counts)''',
     "Counter handles the tally; normalising first stops 'Word' and 'word' being counted separately."),

    (r"flatten|nested list|list of lists", "Flatten a nested list",
     '''def flatten(nested: list) -> list:
    """Flatten one level of nesting into a single list."""
    return [item for group in nested for item in group]


if __name__ == "__main__":
    assert flatten([[1, 2], [3], [], [4, 5]]) == [1, 2, 3, 4, 5]
    print(flatten([["a"], ["b", "c"]]))''',
     "The nested comprehension reads left to right: outer loop first, then inner loop."),

    (r"area of (?:a )?circle|circle area", "Area of a circle",
     '''import math


def circle_area(radius: float) -> float:
    """Return the area of a circle with the given radius."""
    if radius < 0:
        raise ValueError("radius must be non-negative")
    return math.pi * radius ** 2


if __name__ == "__main__":
    assert abs(circle_area(1) - math.pi) < 1e-12
    print(round(circle_area(5), 2))''',
     "Validating the radius up front prevents a meaningless negative area."),

    (r"email (?:validat|check)|valid email|validate.*email", "Validate an email address (simple check)",
     '''import re

_PATTERN = re.compile(r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\\.[A-Za-z]{2,}$")


def is_valid_email(address: str) -> bool:
    """Basic syntactic check. It does NOT prove the mailbox exists."""
    return bool(_PATTERN.fullmatch(address.strip()))


if __name__ == "__main__":
    assert is_valid_email("rasakh@example.com")
    assert not is_valid_email("not-an-email")
    print(is_valid_email("a@b.co"))''',
     "A regex checks the shape only; confirming delivery still requires sending a message."),

    (r"password|random string", "Generate a random password",
     '''import secrets
import string


def make_password(length: int = 16) -> str:
    """Return a cryptographically strong random password."""
    if length < 8:
        raise ValueError("use at least 8 characters")
    alphabet = string.ascii_letters + string.digits + "!@#$%^&*"
    return "".join(secrets.choice(alphabet) for _ in range(length))


if __name__ == "__main__":
    p = make_password()
    assert len(p) == 16
    print(p)''',
     "secrets.choice uses the OS random source; random.choice is not suitable for credentials."),

    (r"simple interest|compound interest|interest", "Compute compound interest",
     '''def compound_interest(principal: float, rate: float, years: int,
                      compounds_per_year: int = 1) -> float:
    """Return the final balance for a nominal annual `rate` given as a decimal."""
    if principal < 0 or years < 0 or compounds_per_year < 1:
        raise ValueError("check principal, years and compounds_per_year")
    return principal * (1 + rate / compounds_per_year) ** (compounds_per_year * years)


if __name__ == "__main__":
    assert round(compound_interest(1000, 0.05, 2), 2) == 1102.50
    print(round(compound_interest(1000, 0.05, 10, 12), 2))''',
     "The rate must be a decimal (0.05 for 5%), not the percentage number."),

    (r"calculator|add.*subtract|basic arithmetic", "A small safe calculator",
     '''import operator

_OPS = {"+": operator.add, "-": operator.sub, "*": operator.mul,
        "/": operator.truediv}


def calculate(left: float, op: str, right: float) -> float:
    """Apply +, -, * or / without using eval()."""
    if op not in _OPS:
        raise ValueError("operator must be one of + - * /")
    if op == "/" and right == 0:
        raise ZeroDivisionError("cannot divide by zero")
    return _OPS[op](left, right)


if __name__ == "__main__":
    assert calculate(6, "*", 7) == 42
    print(calculate(10, "/", 4))''',
     "Dispatching through an explicit dict is safe; eval() on user input is never safe."),

    (r"quadratic|roots of", "Solve a quadratic equation",
     '''import math


def quadratic_roots(a: float, b: float, c: float) -> tuple[float, float] | None:
    """Return the two real roots of ax^2 + bx + c = 0, or None if there are none."""
    if a == 0:
        raise ValueError("a must be non-zero for a quadratic")
    discriminant = b * b - 4 * a * c
    if discriminant < 0:
        return None
    root = math.sqrt(discriminant)
    return (-b + root) / (2 * a), (-b - root) / (2 * a)


if __name__ == "__main__":
    assert quadratic_roots(1, -3, 2) == (2.0, 1.0)
    print(quadratic_roots(1, 0, -9))''',
     "The discriminant decides whether the roots are real before any square root is taken."),

    (r"merge.*dict|combine.*dict|two dictionaries", "Merge two dictionaries",
     '''def merge_dicts(first: dict, second: dict) -> dict:
    """Return a new dict; keys in `second` win when both contain the same key."""
    return {**first, **second}


if __name__ == "__main__":
    assert merge_dicts({"a": 1}, {"a": 2, "b": 3}) == {"a": 2, "b": 3}
    print(merge_dicts({"x": 1}, {"y": 2}))''',
     "Dictionary unpacking creates a new object, so neither input is modified."),

    (r"title case|capitali[sz]e|uppercase", "Title-case a sentence",
     '''def to_title(text: str) -> str:
    """Capitalise the first letter of each word without lowering the rest."""
    return " ".join(word[:1].upper() + word[1:] for word in text.split())


if __name__ == "__main__":
    assert to_title("ryzek ai answers everything") == "Ryzek Ai Answers Everything"
    print(to_title("hello from lahore"))''',
     "str.title() would also mangle apostrophes; word-by-word slicing is predictable."),

    (r"hello world|hello, world|first program", "Hello, world",
     '''def greet(name: str = "world") -> str:
    """Return a greeting. A tiny, complete, runnable Python function."""
    return f"Hello, {name}!"


if __name__ == "__main__":
    assert greet() == "Hello, world!"
    assert greet("Rasakh") == "Hello, Rasakh!"
    print(greet())''',
     "A default argument makes the function useful with or without a name."),
]


def _generic_code(task: str) -> Tuple[str, str]:
    words = re.findall(r"[a-z]+", (task or "").lower())
    stop = {"a", "an", "the", "that", "which", "to", "for", "simple", "python",
            "function", "write", "please", "me", "code", "program", "script",
            "in", "with", "using", "of", "and", "is", "it", "something"}
    name_words = [w for w in words if w not in stop][:3]
    fname = "_".join(name_words) if name_words else "solve_task"
    if fname[0].isdigit():
        fname = "task_" + fname
    code = f'''def {fname}(value):
    """{_cap(task[:110])}

    A clean, runnable starting point: the signature, validation, docstring,
    return value and a test block are already in place. Replace the body with
    your exact rule - or tell me the rule and I will write it for you.
    """
    if value is None:
        raise ValueError("value must not be None")
    result = value
    return result


if __name__ == "__main__":
    assert {fname}("example") == "example"
    assert {fname}(0) == 0
    print({fname}("your input here"))'''
    return code, "I could not match a specific algorithm in your wording, so this is a clean, runnable scaffold rather than a guess."



# ---------------------------------------------------------------------------
# Email
# ---------------------------------------------------------------------------


def _email(meta: Dict[str, str], depth: str) -> str:
    T = meta["topic"]
    rec = meta["recipient"]
    tone = meta["tone"]
    purpose = meta["purpose_phrase"]
    cap = _cap(T)
    low_p = (meta["purpose"] + " " + T).lower()
    if "apolog" in low_p:
        subject = f"My apologies regarding {T}"
    elif "invit" in low_p:
        subject = f"Invitation: {cap}"
    elif "complain" in low_p or "concern" in low_p:
        subject = f"Concern regarding {T}"
    elif "thank" in low_p:
        subject = f"Thank you - {T}"
    elif "request" in low_p or "asking" in low_p or "leave" in low_p:
        subject = f"Request regarding {T}"
    else:
        subject = f"Regarding {T}"

    sal = _salutation(rec, tone)
    closing = _signoff(tone)
    recipient_line = _recipient_display(rec)

    body = "\n".join([
        f"Subject: {subject}",
        f"To: {recipient_line}",
        "",
        sal,
        "",
        "I hope this message finds you well.",
        "",
        f"I am writing {purpose}. I wanted to put the details in writing so that everything is "
        "clear and easy to refer back to.",
        "",
        f"In short, this concerns {T}. The relevant details are [add the dates, reference numbers "
        "or specifics here], and I have kept them together in one place so nothing is missed.",
        "",
        "I would be grateful if you could [state the exact action you need] at your earliest "
        "convenience. If a different approach would work better, or if you need anything further "
        "from me, please let me know and I will arrange it straight away.",
        "",
        "Thank you for your time and understanding.",
        "",
        closing,
        "[Your Name]",
        "[Your contact details]",
    ])
    piece = "**" + subject + "**\n\n" + _fence(body, "text")
    adapt = [
        "Replace every `[placeholder]` with your real details - especially the dates and your name.",
        "Make the third paragraph concrete: one date, one number or one clear request is worth more than a long explanation.",
        "For a friend, shorten it to two sentences and swap the closing to 'Talk soon,'.",
        f"The tone here is **{tone}**; say 'make it more formal' or 'make it casual' to change it.",
    ]
    why_list = [
        "The subject line says what the email is about, so it can be found again later.",
        "The purpose appears in the first two lines - readers decide in seconds whether to keep reading.",
        "One paragraph gives context, one gives detail, one states the exact action; ending with thanks keeps it courteous.",
        "Placeholders are deliberate: I will not invent a date, a name or a reason you did not give me.",
    ]
    checklist = [
        "Search the draft for `[` and fill in every placeholder.",
        "Check the recipient's name and title are spelled correctly.",
        "Read the request out loud - if you cannot say what you want in one sentence, tighten it.",
        "Attach any supporting files before sending, and mention them in the third paragraph.",
    ]
    extra = ("### A shorter version\n\n" + _fence("\n".join([
        f"Subject: {subject}", "", sal, "",
        f"I am writing {purpose}. Could you please [state the action] by [date]?",
        "Thank you for your help.", "", closing, "[Your Name]"]), "text") +
        "\n\n### Word choice that helps\n\n"
        "- Replace 'I wanted to' with 'I am writing to' - it is direct without being abrupt.\n"
        "- Use 'at your earliest convenience' only when there is genuinely no deadline; otherwise name the date.\n"
        "- Avoid 'just' and 'sorry to bother you' in a formal request; they weaken a reasonable ask.")
    return _finish(piece, meta, depth, adapt, why_list, checklist, extra,
                   title="Email ready to copy")


# ---------------------------------------------------------------------------
# Letter
# ---------------------------------------------------------------------------


def _letter(meta: Dict[str, str], depth: str) -> str:
    T = meta["topic"]
    rec = meta["recipient"]
    tone = meta["tone"]
    purpose = meta["purpose_phrase"]
    cap = _cap(T)
    sal = _salutation(rec, tone)
    closing = "Yours faithfully," if (tone == "formal" and not rec) else _signoff(tone)
    recipient_line = rec if rec else "The Recipient"

    if tone == "formal":
        body = "\n".join([
            "[Your Name]",
            "[Your Address]",
            "[City, Postal Code]",
            "[Email] · [Phone]",
            "",
            "[Date]",
            "",
            f"To",
            f"{_cap(recipient_line)}",
            "[Recipient's Address]",
            "",
            f"Subject: {T}",
            "",
            sal,
            "",
            f"I am writing {purpose}. I have set out the relevant details below so that the matter "
            "can be considered without further correspondence.",
            "",
            f"This concerns {T}. [State the background in one or two sentences, including any "
            "dates, reference numbers or previous conversations.] The important point is that "
            "the matter is still open and a decision or confirmation is needed.",
            "",
            "I would therefore be grateful if you could [state the exact action required] by "
            "[date]. Should you require any additional information or documentation, please do "
            "not hesitate to contact me and I will provide it promptly.",
            "",
            "Thank you for your time and consideration. I look forward to your response.",
            "",
            closing,
            "",
            "[Signature]",
            "[Your Name]",
        ])
    else:
        body = "\n".join([
            "[Date]",
            "",
            sal,
            "",
            "I hope you are doing well. It has been a while since we last caught up, and I "
            "thought I would write rather than send another quick message.",
            "",
            f"I wanted to tell you about {T}. [Add the real story here - what happened, who was "
            "there, and the bit that made you laugh.] Things on my side have been busy but good, "
            "and I have been meaning to ask how everything is with you.",
            "",
            "Write back when you get a chance, or just call - either works. I would really like "
            "to hear what you have been up to.",
            "",
            closing,
            "[Your Name]",
        ])
    piece = "**" + cap + "**\n\n" + _fence(body, "text")
    adapt = [
        "Fill in every `[placeholder]`; a letter with an unfilled address looks unfinished.",
        "For a school or office letter, keep the subject line to one short noun phrase.",
        "Add one concrete detail to the middle paragraph - a date, a name or a number.",
        f"The tone here is **{tone}**; ask for the other tone and I will rewrite it.",
    ]
    why_list = [
        "A formal letter puts the sender, date and recipient before the salutation so it can be filed and referenced.",
        "The opening sentence states the purpose immediately; the middle gives evidence; the last paragraph asks for a specific action.",
        "An informal letter drops the address blocks and leads with the relationship instead.",
        "Square brackets mark facts I do not have, so nothing is invented on your behalf.",
    ]
    checklist = [
        "Confirm the spelling of the recipient's name and their correct title.",
        "Check the date and any reference numbers.",
        "Sign it, and keep a copy for your own record.",
    ]
    extra = ("### Formal vs informal at a glance\n\n"
             "| | Formal | Informal |\n|---|---|---|\n"
             "| Opening | Dear Sir/Madam, | Hi [name], |\n"
             "| Purpose | First sentence | After the greeting |\n"
             "| Closing | Yours sincerely/faithfully, | Warm regards / Talk soon, |\n"
             "| Contractions | Avoid | Fine |\n\n"
             "### A one-paragraph core\n\n" + _fence(
                 f"{sal}\n\nI am writing {purpose}. {cap} needs [action] by [date]; "
                 "please let me know if anything else is required.\n\n" + closing, "text"))
    return _finish(piece, meta, depth, adapt, why_list, checklist, extra,
                   title="Letter ready to copy")


# ---------------------------------------------------------------------------
# Essay
# ---------------------------------------------------------------------------


def _essay(meta: Dict[str, str], depth: str) -> str:
    """A real essay about the topic, built from checked material.

    Earlier versions produced a generic lecture on 'how to discuss a topic'.
    This one opens with the definition, then uses actual retrieved sentences
    about the subject for the mechanism, evidence and response.
    """
    T = meta["topic"]
    cap = _cap(T)
    facts = list(meta.get("material") or [])
    used: set = set()

    def take(n: int) -> List[str]:
        got = []
        for item in facts:
            if item in used:
                continue
            used.add(item)
            got.append(item)
            if len(got) >= n:
                break
        return got

    lead = take(1)
    opening = (lead[0] if lead else
               f"{cap} is a subject that rewards a careful look rather than a quick opinion.")
    intro = (opening + " This essay sets out what it is, what drives it, what the observed "
             "evidence shows and where the honest limits lie, before drawing a practical conclusion.")

    b = take(2)
    background = ("The starting point is the mechanism. " + " ".join(b)) if b else (
        f"The starting point is to define {T} narrowly enough that the discussion can be checked.")
    background += (" That mechanism matters because it explains why the effects appear where they "
                   "do, rather than simply asserting that they do.")

    m = take(3)
    main = ("What follows can be stated plainly. " + " ".join(m)) if m else (
        f"The consequences of {T} can be traced through a chain of cause and effect.")
    main += (" Each of these claims is in principle measurable, which is what separates an "
             "explanation from a slogan: a reader can ask for the record behind it.")

    counter = (f"A fair objection is that a single account of {T} can flatten important "
               "differences between places, periods and scales. Data gathered in one setting "
               "does not automatically transfer to another, and a rule that is useful in general "
               "can be misleading in a particular case. Recognising that does not defeat the "
               "argument; it states the boundary inside which the argument should be used.")

    r = take(2)
    response = ("Those limits can be handled without abandoning the main point. " +
                (" ".join(r) if r else
                 f"The useful response to {T} is to separate what is well established from what "
                 "is still being measured."))
    response += (" In practice that means stating the assumption, testing it against one concrete "
                 "case, and revising the wording when the case does not fit.")

    conclusion = (f"Taken together, the evidence on {T} supports a clear but qualified conclusion: "
                  "the underlying mechanism is understood, the consequences are observable, and "
                  "most of the remaining disagreement concerns scale, timing and the best response. "
                  f"Anyone writing further about {T} should begin with a definition, keep one "
                  "checkable example in view, and say openly which parts are still uncertain. "
                  "That is a stronger position than a confident claim with no evidence behind it.")

    paras = [intro, background, main, counter, response, conclusion]
    if depth == "quick":
        chosen = [intro, main, conclusion]
    elif depth == "standard":
        chosen = [intro, background, main, conclusion]
    else:
        chosen = paras

    out = [f"# {cap}", "", "## Introduction", "", chosen[0]]
    if len(chosen) > 1:
        out += ["", "## Background and mechanism", "", chosen[1]]
    if len(chosen) > 2:
        out += ["", "## What the evidence shows", "", chosen[2]]
    if len(chosen) > 4:
        out += ["", "## A counterargument", "", chosen[3]]
        out += ["", "## Response and practical implications", "", chosen[4]]
    out += ["", "## Conclusion", "", chosen[-1]]

    if facts:
        out += ["", "## Sources for the factual claims", ""]
        live = list(meta.get("sources") or [])
        if live:
            out += ["I read these live pages while writing this essay:", ""]
            seen_urls = set()
            for src in live[:6]:
                url = src.get("url") or ""
                if not url or url in seen_urls:
                    continue
                seen_urls.add(url)
                label = {"google": "Google", "wikipedia": "Wikipedia",
                         "simplewiki": "Simple Wikipedia", "bing": "Bing",
                         "duckduckgo": "DuckDuckGo", "wikidata": "Wikidata",
                         "webpages": "Web page", "openlibrary": "Open Library",
                         "github": "GitHub", "stackoverflow": "Stack Overflow"}.get(
                             src.get("source"), "Web")
                out.append(f"- [{src.get('title', 'Source')}]({url}) — {label}")
            out += ["", "The rest comes from the Ryzek AI curated knowledge base and cached "
                    "Wikipedia articles. Verify any figure or date against a primary source "
                    "before submitting."]
        else:
            out += ["- Ryzek AI curated knowledge base and cached Wikipedia articles retrieved for "
                    "this essay. Verify any figure or date against a primary source before submitting."]
    else:
        out += ["", "## A note on this draft", "",
                f"I did not have checked material about {T}, so the paragraphs above give you a "
                "complete, correctly structured essay without inventing facts. Tell me the topic "
                "in one more word, or paste your source text, and I will rewrite it with real detail."]

    if depth == "exhaustive":
        out += ["", "## Suggested structure for a longer version", "",
                "1. Introduction with a one-sentence thesis.",
                "2. Definitions and scope.",
                "3. Three body paragraphs: cause, evidence and implication.",
                "4. A genuine counterargument, stated fairly.",
                "5. Your response to that counterargument.",
                "6. Conclusion that says what should happen next.", "",
                "## Where to add your own evidence", "",
                f"After the third paragraph, insert one specific, checkable example about {T} - "
                "a date, a figure, a named study or a first-hand observation - and cite it."]

    piece = "\n".join(out)
    adapt = [
        f"Add one real, checkable example about {T} in the third paragraph - a date, a figure or a named source.",
        "Replace the first sentence with a sharper hook if this is for an exam or a submission.",
        ("Shorten by dropping the counterargument section, or lengthen by adding a second "
         "example." if depth in ("deep", "exhaustive") else
         "Ask for the Deep or Exhaustive depth to add a counterargument and a response section."),
        "Change the tone to formal, persuasive or personal and I will rewrite it in that voice.",
    ]
    why_list = [
        "The opening is the actual definition of the topic, not a lecture about essays.",
        "Body paragraphs use retrieved factual sentences about the subject, joined by signposting so they read as prose.",
        "The counterargument is stated fairly rather than as a straw man.",
        "The conclusion draws a practical implication instead of repeating the introduction.",
    ]
    checklist = [
        "Check that every paragraph starts with a claim, not a fact dump.",
        "Verify any date, number or quotation you add.",
        "Read the first and last paragraphs back to back; they should agree.",
        "Confirm the word count and citation style your teacher or editor asked for.",
    ]
    extra = ("### A one-paragraph abstract\n\n" + _fence(
        f"{cap} is examined through its definition, the mechanism behind it and the observable "
        "evidence, followed by the main objection to a general account. The essay argues that a "
        "clear, testable framing is more useful than a broad claim, while acknowledging that "
        "context sets real limits.", "text") +
        "\n\n### Common mistakes\n\n"
        "- Repeating the introduction in the conclusion.\n"
        "- Using 'everyone knows' or 'it is obvious' in place of evidence.\n"
        "- Presenting a counterargument only in order to dismiss it in one line.\n"
        "- Adding long quotations without explaining what they show.")
    return _finish(piece, meta, depth, adapt, why_list, checklist, extra,
                   title="Essay: " + cap)


# ---------------------------------------------------------------------------
# Story, poem, speech, article, report, note
# ---------------------------------------------------------------------------


def _story(meta: Dict[str, str], depth: str) -> str:
    T = meta["topic"] or "an ordinary Tuesday"
    cap = _cap(T)
    out = [f"# {cap}", "",
           f"Nobody expected {T} to matter quite as much as it did. It began the way these "
           "things usually begin: with a small thing out of place, and somebody patient enough "
           "to notice.", "",
           "The morning was quiet. A cup of tea went cold on the corner of the table, the fan "
           "turned slowly, and outside the city was still deciding whether to wake up. Then the "
           "letter arrived - no stamp, no return address, just a name written in careful, "
           "unhurried handwriting.", "",
           f"Inside was a single question about {T}. It was not a difficult question. That was "
           "the strange part. Anyone could have answered it in a sentence, and yet nobody had "
           "thought to ask it before.", "",
           "By afternoon the answer had grown into a plan, and the plan had acquired a problem: "
           "it required three people who had not spoken to one another in years to sit at the "
           "same table. They did. There was awkwardness, then tea, and then - slowly - the kind "
           "of conversation that only happens when somebody finally asks the obvious thing out loud.", "",
           "By evening everything looked the same as it had that morning: the cold cup, the "
           "turning fan, the street settling down for the night. But the small thing out of "
           "place had been put right, and everyone at the table knew it. That is usually how "
           "the important days go - almost indistinguishable from the ordinary ones until you "
           "look back."]
    if depth == "quick":
        out = out[:6] + ["", "And that was how it ended: quietly, and well."]
    piece = "\n".join(out)
    return _finish(piece, meta, depth,
                   ["Change the setting, the season or the three characters to make it yours.",
                    "Add one line of dialogue to the middle scene - it brings the table to life.",
                    "Tell me 'make it funny / sad / mysterious' and I will rewrite the tone."],
                   ["A short story works by a small disruption, a choice, and a return that is subtly different.",
                    "Concrete objects (a cold cup, a slow fan) do more world-building than adjectives.",
                    "The last line echoes the first so the story feels finished."],
                   ["Check the tense stays consistent.", "Read the dialogue aloud.",
                    "Cut any sentence that does not change something."],
                   "### A six-line version\n\n" + _fence(
                       f"It began with {T}.\nNobody noticed at first.\n"
                       "Then someone asked the obvious question.\n"
                       "Three people had to talk again.\n"
                       "By evening the room looked the same.\n"
                       "Nothing was the same.", "text"),
                   title="Short story: " + cap)


def _poem(meta: Dict[str, str], depth: str) -> str:
    T = meta["topic"] or "the morning"
    cap = _cap(T)
    words = [w for w in re.findall(r"[a-z]+", T.lower()) if len(w) > 3][:4]
    motif = words[-1] if words else "light"
    stanzas = [
        f"Before the name of {T} was spoken,\n"
        "the room was only a room,\nthe window only a square of weather,\n"
        "and the clock in no particular hurry.",
        f"Then {motif} arrived without an argument,\n"
        "the way small truths do —\n"
        "not asking to be believed,\n"
        "only asking to be noticed.",
        f"Now everything keeps a little of {T}:\n"
        "the cup, the chair, the unwritten line,\n"
        "and the patient space between two words\n"
        "where an answer might still begin.",
    ]
    if depth in ("deep", "exhaustive"):
        stanzas.append(
            "So leave the door the way you found it —\n"
            "open just enough for the ordinary,\n"
            "and for the extraordinary\n"
            "that has been standing there all along.")
    piece = "**" + cap + "**\n\n" + _fence("\n\n".join(stanzas), "text")
    return _finish(piece, meta, depth,
                   ["Tell me a mood - joyful, melancholy, playful - and I will change the imagery.",
                    "Ask for a rhyming version, a sonnet, a ghazal or a haiku and I will use that form.",
                    "Replace the motif word with one that means something to you."],
                   ["Free verse relies on concrete images rather than rhyme to hold the reader.",
                    "The same object returns in the first and last stanza so the poem closes a circle.",
                    "Line breaks carry the pauses - there is no punctuation doing that work."],
                   ["Read it aloud once; keep only the lines you can say without stumbling.",
                    "Cut every abstract word you can replace with a thing you can see."],
                   "### A haiku on the same subject\n\n" + _fence(
                       f"Quiet morning light\n{motif} rests on the window sill\n{nothing_to_five(T)}", "text"),
                   title="Poem: " + cap)


def nothing_to_five(t: str) -> str:
    return ("a small answer waits" if len(t) % 2 else "nothing asks for more")


def _speech(meta: Dict[str, str], depth: str) -> str:
    T = meta["topic"] or "the idea in front of us"
    cap = _cap(T)
    fact = (meta.get("material") or [""])[0]
    out = [f"# A short speech on {cap}", "",
           "Good morning everyone.", "",
           "Thank you for being here. I want to talk about something that is easy to overlook "
           f"precisely because it is right in front of us: {T}. I will keep this to three points, "
           "and then I will stop.", "",
           "**First, why it matters.** " +
           (fact if fact else f"Almost every reason we are in this room touches {T} in some way.") +
           " When we treat it as background noise we make decisions in the dark; when we name it "
           "plainly, the choices in front of us get much simpler.", "",
           "**Second, what we can actually do.** Not a grand plan - three ordinary things. We can "
           "ask a better question before we act. We can write down what we assume so that someone "
           "else can check it. And we can agree in advance on what would count as progress. None "
           "of those require permission, budget or a committee.", "",
           "**Third, what happens if we do nothing.** Nothing dramatic. That is the risk. Things "
           "carry on almost exactly as they are, and a year from now we will have the same "
           "conversation with slightly less energy. Small, deliberate changes beat a dramatic "
           "one that never starts.", "",
           "So here is my ask: choose one of those three things and do it this week. Not all of "
           "them - one. Tell someone else which one you chose.", "",
           "Thank you for your time, and I am happy to take questions."]
    if depth == "quick":
        out = [out[0], "", out[2], "", out[4], "", out[8], "", out[-1]]
    piece = "\n".join(out)
    return _finish(piece, meta, depth,
                   ["Add a personal anecdote after the opening - it earns the audience's attention.",
                    "Tell me the audience (class, team, wedding, conference) and I will change the register.",
                    "Ask for a two-minute or a ten-minute version and I will resize it."],
                   ["A speech says its shape out loud: three points, then stop.",
                    "Short sentences survive being heard better than long ones.",
                    "Ending with one concrete ask converts agreement into action."],
                   ["Time it aloud; spoken words take longer than read ones.",
                    "Cut any statistic you cannot source on the spot.",
                    "Practise the first and last sentences until you do not need notes."],
                   "### One-line opener alternatives\n\n" + _fence(
                       f"- \"I want to talk about {T}, and I want to be brief.\"\n"
                       f"- \"Everything I am about to say about {T} fits on one slide.\"\n"
                       "- \"Here is the question I think we have all been avoiding.\"", "text"),
                   title="Speech: " + cap)


def _article(meta: Dict[str, str], depth: str) -> str:
    T = meta["topic"] or "the subject"
    cap = _cap(T)
    facts = list(meta.get("material") or [])
    f1 = facts[0] if facts else ""
    f2 = " ".join(facts[1:4]) if len(facts) > 1 else ""
    what_it_is = (f2.strip() if f2.strip() else
                  f"Start with a definition you can defend. In the case of {T}, name the boundary: "
                  "which situations count, which do not, and what a reader would see if the "
                  "definition were wrong.")
    why_it_matters = ("These details change what you do next: they tell you which measurement to "
                      "record, which assumption to test and which result would prove the account "
                      "wrong. The practical value is being able to act and then verify what happened.")
    out = [f"# {cap}: a practical explainer", "",
           f"*What {T} actually means, why it matters, and what to do with the answer.*", "",
           "## The short version", "",
           (f1 if f1 else f"{cap} is easier to understand once it is broken into three questions: "
            "what it is, what it changes, and what we can check."), "",
           "## What it is", "", what_it_is, "",
           "## Why it matters", "", why_it_matters, "",
           "## What to watch out for", "",
           "Two traps recur. The first is treating one vivid example as a general rule. The "
           "second is using a technical word as though it were an explanation. Both are easy to "
           "spot once you ask for a second example and a plain-language restatement.", "",
           "## The takeaway", "",
           f"If you remember one thing about {T}, make it this: define the terms, name the "
           "assumption, and keep one checkable example nearby. That habit outlasts any single answer."]
    if depth == "quick":
        out = out[:8] + ["", "## The takeaway", "", out[-1]]
    piece = "\n".join(out)
    return _finish(piece, meta, depth,
                   ["Add a real example, a figure or a quotation with a source in the second section.",
                    "Tell me the publication and audience and I will adjust the voice.",
                    "Ask for a listicle, an opinion piece or a news-style version."],
                   ["A deck under the headline tells the reader what they will get.",
                    "Short sections with descriptive subheads make the piece skimmable.",
                    "The takeaway repeats the framing so the article feels complete."],
                   ["Verify every number and name you add.", "Check the headline matches the content.",
                    "Read the first two paragraphs alone - they should stand on their own."],
                   "### Outline you can reuse\n\n" + _fence(
                       "1. Headline + one-line deck\n2. The short version\n3. Definition\n"
                       "4. Why it matters\n5. Common traps\n6. Takeaway / next step", "text"),
                   title="Article: " + cap)


def _report(meta: Dict[str, str], depth: str) -> str:
    T = meta["topic"] or "the matter under review"
    cap = _cap(T)
    out = [f"# Report: {cap}", "",
           "**Prepared for:** [Recipient]  ·  **Date:** [Date]  ·  **Status:** Draft", "",
           "## Executive summary", "",
           f"This report considers {T}. Its purpose is to set out what is known, what remains "
           "unconfirmed and what action is recommended. The central finding is that a decision "
           "can be made now provided the two open items listed below are confirmed first.", "",
           "## 1. Background", "",
           f"[Describe how {T} came to require attention, who is involved and the period covered. "
           "Keep this to factual, dated statements.]", "",
           "## 2. Findings", "",
           "- **Finding 1:** [State an observation, then the evidence for it.]",
           "- **Finding 2:** [State a second observation and any measurement supporting it.]",
           "- **Finding 3:** [State what could not be confirmed and why.]", "",
           "## 3. Analysis", "",
           "Taken together, the findings point to a limited, reversible step rather than a broad "
           "change. The main risk is acting on an unconfirmed assumption; the main cost of delay "
           "is missing the window in which the small step still works.", "",
           "## 4. Recommendation", "",
           "1. Confirm [open item one] by [date].",
           "2. Confirm [open item two] and record the source.",
           "3. Proceed with [proposed action], then review the outcome after [period].", "",
           "## 5. Limitations", "",
           "This draft uses only the information supplied in the request. Every bracketed item "
           "must be checked against a primary source before the report is circulated.", ""]
    piece = "\n".join(out)
    return _finish(piece, meta, depth,
                   ["Fill in every bracket with a date, name, number and source.",
                    "Tell me the real findings and I will write a finished report, not a template.",
                    "Ask for a one-page version or a slide-ready summary."],
                   ["The executive summary is written so a busy reader can stop after it and still know the recommendation.",
                    "Findings and analysis are separate: one says what was observed, the other says what it means.",
                    "A limitations section is what makes the rest credible."],
                   ["Verify every figure and attach the source.", "Check that the recommendation matches the findings.",
                    "Remove any bracket before circulating."],
                   "### One-paragraph summary\n\n" + _fence(
                       f"{cap} can proceed on a limited basis once [open item one] and "
                       "[open item two] are confirmed. The recommended action is reversible, "
                       "low-cost and reviewable after [period]; a broader change is not yet justified.", "text"),
                   title="Report: " + cap)


def _note(meta: Dict[str, str], depth: str) -> str:
    T = meta["topic"] or "today"
    cap = _cap(T)
    body = f"""Hi [Name],

Just a quick note about {T}.

[One sentence with the actual point — a time, a place, a decision or a question.]

Let me know what works on your side, and I will take it from there.

Thanks,
[Your Name]"""
    piece = "**" + cap + "**\n\n" + _fence(body, "text")
    return _finish(piece, meta, depth,
                   ["Put the single most important fact in the middle sentence.",
                    "Delete the greeting if it is a chat message rather than a note.",
                    "Ask for a firmer, warmer or more formal version."],
                   ["A short note has one job, so it should contain one point.",
                    "Ending with an offer to handle the next step keeps it moving.",
                    "Placeholders keep me from inventing your details."],
                   ["Check the name and the time.", "Remove anything that is not the point."],
                   "### Even shorter\n\n" + _fence(
                       f"Quick one: {T} — [the point]. Does [option] work for you?", "text"),
                   title="Note ready to copy")


_BUILDERS = {
    "code": lambda m, d: _code(m, d), "email": _email, "essay": _essay, "letter": _letter,
    "story": _story, "poem": _poem, "speech": _speech, "article": _article,
    "urdu_poem": lambda m, d: _urdu_poem(m, d),
    "report": _report, "note": _note,
}



def _urdu_poem(meta: Dict[str, str], depth: str) -> str:
    """Real Urdu verse, not an explanation of what poetry is."""
    return ryzek_urdu.write_urdu(meta.get("topic", ""), depth)


# ---------------------------------------------------------------------------
# Simple Python (v2.5)
#
# The older templates below are still valid Python and are kept for the tests,
# but they were too advanced for everyday use: type hints, docstrings, input
# validation, test harnesses and a `__main__` block for a three-line function.
# Answers now use these short, beginner-level versions instead.
# ---------------------------------------------------------------------------

SIMPLE_LIBRARY: List[Tuple[str, str, str, str]] = [
    (r"revers\w*\s+(?:a\s+)?(?:string|text|word)|reverse\s+string", "Reverse a string",
     'def reverse_string(text):\n    return text[::-1]\n\nprint(reverse_string("Python"))',
     "The slice [::-1] reads the text from the last character to the first."),
    (r"palindrom", "Check for a palindrome",
     'def is_palindrome(text):\n    clean = "".join(c.lower() for c in text if c.isalnum())\n'
     '    return clean == clean[::-1]\n\nprint(is_palindrome("level"))',
     "It removes spaces and punctuation first, then compares the text with its reverse."),
    (r"factorial", "Find a factorial",
     'def factorial(n):\n    total = 1\n    for i in range(2, n + 1):\n'
     '        total *= i\n    return total\n\nprint(factorial(5))',
     "A loop multiplies every number from 2 up to n."),
    (r"fibonacci|fib\b", "Print a Fibonacci number",
     'def fibonacci(n):\n    a, b = 0, 1\n    for _ in range(n):\n'
     '        a, b = b, a + b\n    return a\n\nprint(fibonacci(10))',
     "Each step moves the pair of numbers one place along the sequence."),
    (r"fizzbuzz|fizz buzz", "FizzBuzz",
     'def fizzbuzz(n):\n    for i in range(1, n + 1):\n'
     '        if i % 15 == 0:\n            print("FizzBuzz")\n'
     '        elif i % 3 == 0:\n            print("Fizz")\n'
     '        elif i % 5 == 0:\n            print("Buzz")\n'
     '        else:\n            print(i)\n\nfizzbuzz(15)',
     "Check 15 first, because a multiple of 15 is also a multiple of 3 and 5."),
    (r"prime", "Check for a prime number",
     'def is_prime(n):\n    if n < 2:\n        return False\n'
     '    for i in range(2, int(n ** 0.5) + 1):\n'
     '        if n % i == 0:\n            return False\n    return True\n\nprint(is_prime(97))',
     "It only tests divisors up to the square root, which is enough and much faster."),
    (r"count\w*\s+words|word count", "Count words",
     'def count_words(text):\n    return len(text.split())\n\nprint(count_words("Ryzek writes clearly"))',
     "split() cuts the text at spaces, and len() counts the pieces."),
    (r"average|mean of", "Find the average",
     'def average(numbers):\n    return sum(numbers) / len(numbers)\n\nprint(average([4, 8, 15]))',
     "Add all the numbers, then divide by how many there are."),
    (r"largest|biggest|maximum|max\w*\s+(?:of|in)", "Find the largest number",
     'def largest(numbers):\n    best = numbers[0]\n    for n in numbers:\n'
     '        if n > best:\n            best = n\n    return best\n\nprint(largest([3, 19, 7]))',
     "It keeps the biggest value seen so far in a variable called best."),
    (r"duplicate|unique|remove repeats", "Remove duplicates",
     'def unique(items):\n    result = []\n    for item in items:\n'
     '        if item not in result:\n            result.append(item)\n    return result\n\nprint(unique([1, 2, 2, 3]))',
     "It only adds an item the first time it appears, so the order stays the same."),
    (r"sort\w*\s+(?:a\s+)?(?:list|numbers|array)", "Sort a list",
     'def sort_numbers(numbers):\n    return sorted(numbers)\n\nprint(sort_numbers([5, 2, 9, 1]))',
     "sorted() returns a new list in order and leaves the original unchanged."),
    (r"quadratic", "Solve a quadratic equation",
     'import math\n\ndef solve_quadratic(a, b, c):\n    d = b * b - 4 * a * c\n'
     '    if d < 0:\n        return []\n'
     '    return [(-b + math.sqrt(d)) / (2 * a), (-b - math.sqrt(d)) / (2 * a)]\n\n'
     'print(solve_quadratic(1, -3, 2))',
     "It uses the quadratic formula and returns an empty list when there are no real roots."),
    (r"celsius|fahrenheit|temperature", "Convert Celsius to Fahrenheit",
     'def celsius_to_fahrenheit(c):\n    return c * 9 / 5 + 32\n\nprint(celsius_to_fahrenheit(100))',
     "Multiply by nine fifths, then add 32."),
    (r"vowel", "Count vowels",
     'def count_vowels(text):\n    return sum(1 for c in text.lower() if c in "aeiou")\n\n'
     'print(count_vowels("Ryzek"))',
     "It checks each letter and adds one whenever the letter is a vowel."),
    (r"e-?mail|valid email", "Check an email address",
     'def is_email(text):\n    return "@" in text and "." in text and " " not in text\n\n'
     'print(is_email("a@b.com"))',
     "This is a quick check, not a full validator, but it catches the common mistakes."),
    (r"gcd|highest common|greatest common", "Find the GCD",
     'def gcd(a, b):\n    while b:\n        a, b = b, a % b\n    return a\n\nprint(gcd(48, 18))',
     "Euclid's method keeps replacing the pair with the smaller number and the remainder."),
    (r"leap year", "Check a leap year",
     'def is_leap_year(year):\n'
     '    return year % 4 == 0 and (year % 100 != 0 or year % 400 == 0)\n\n'
     'print(is_leap_year(2024))',
     "Years divisible by 100 are not leap years unless they are also divisible by 400."),
    (r"digit\w*\s+sum|sum of digits", "Add the digits of a number",
     'def digit_sum(n):\n    return sum(int(d) for d in str(abs(n)))\n\nprint(digit_sum(1234))',
     "It turns the number into text so each digit can be turned back into a number."),
    (r"second largest|second biggest", "Find the second largest number",
     'def second_largest(numbers):\n    return sorted(set(numbers))[-2]\n\n'
     'print(second_largest([4, 1, 9, 9, 3]))',
     "set() removes repeats, sorted() orders them, and [-2] takes the second from the end."),
    (r"word frequen|count occurrences|frequency", "Count how often each word appears",
     'def word_counts(text):\n    counts = {}\n    for word in text.lower().split():\n'
     '        counts[word] = counts.get(word, 0) + 1\n    return counts\n\n'
     'print(word_counts("hi hi hello"))',
     "A dictionary stores one number per word and adds one each time it appears."),
    (r"multiplication table|times table", "Print a multiplication table",
     'def table(n):\n    for i in range(1, 11):\n        print(n, "x", i, "=", n * i)\n\ntable(5)',
     "A loop from 1 to 10 prints one row of the table at a time."),
    (r"circle|area", "Find the area of a circle",
     'import math\n\ndef circle_area(radius):\n    return math.pi * radius * radius\n\n'
     'print(circle_area(3))',
     "The formula is pi times the radius squared."),
    (r"title case|capitali\w*\s+words", "Capitalise each word",
     'def title_case(text):\n    return " ".join(w.capitalize() for w in text.split())\n\n'
     'print(title_case("hello from ryzek"))',
     "split() makes the words, capitalize() fixes each one, and join() puts them back."),
    (r"read\w*\s+(?:a\s+)?file|open a file", "Read a text file",
     'def read_file(path):\n    with open(path, "r") as f:\n        return f.read()\n\n'
     'print(read_file("notes.txt"))',
     "The with statement closes the file for you, even if something goes wrong."),
    (r"random|pick one|choose", "Pick a random item",
     'import random\n\ndef pick_one(items):\n    return random.choice(items)\n\n'
     'print(pick_one(["tea", "coffee", "water"]))',
     "random.choice() picks one item from a list."),
]


def _simple_generic(task: str) -> Tuple[str, str]:
    label = (task or "value")[:40].replace('"', "'")
    code = ('def solve(value):\n'
            '    # Step 1: take the input\n'
            '    result = value\n'
            '    # Step 2: change it here\n'
            '    # Step 3: hand the answer back\n'
            '    return result\n\n'
            'print(solve("' + label + '"))')
    return code, ("I do not have an exact rule for that yet, so this is a clean starting "
                  "function. Tell me the input, the output and one example and I will "
                  "fill in step 2 for you.")


def _code(meta: Dict[str, str], depth: str) -> str:
    """Short, beginner-level Python: one function, one example, plain notes."""
    task = meta["topic"] or meta["raw"]
    matched = None
    for pattern, title, code, why in SIMPLE_LIBRARY:
        if re.search(pattern, task, re.I):
            matched = (title, code, why)
            break
    if matched:
        title, code, why = matched
    else:
        code, why = _simple_generic(task)
        title = "A simple starting function"

    out = ["## Python function: " + title, "", _fence(code, "python"), "",
           "This is the whole function. " + why + " It uses only built-in Python, "
           "so you can paste it into a `.py` file and run it straight away.", ""]
    if depth == "quick":
        return "\n".join(out).strip() + "\n"
    out += ["### Try it", "",
            "- Change the value inside `print(...)` and run the file again.",
            "- Add a second example with a different input to see what changes.",
            "- If you want a different rule, tell me the input and the output.", ""]
    if depth in ("deep", "exhaustive"):
        out += ["### Why it stays short", "",
                "Beginners do not need type hints, docstrings or a test harness to see how "
                "a function works. Once the idea is clear, you can add those later. "
                "Ask for a longer version only if you actually need one.", ""]
    return "\n".join(out).strip() + "\n"


def write(text: str, depth: str = "standard",
          material: Optional[List[str]] = None,
          sources: Optional[List[Dict[str, str]]] = None) -> Optional[str]:
    """Produce a finished piece of writing, or None if this is not a writing task."""
    meta = detect(text)
    if not meta:
        return None
    meta["material"] = material or []
    meta["sources"] = sources or []
    try:
        return _BUILDERS.get(meta["genre"], _note)(meta, depth)
    except Exception:
        return None
