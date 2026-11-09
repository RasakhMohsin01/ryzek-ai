#!/usr/bin/env python3
"""
Ryzek AI - warm, human small talk.

`hey hw r u doin today`, `hi`, `Good Morning`, `thanks`, `bye` are real
messages and deserve a real, short, friendly answer. They must never fall
through to the research pipeline and come back as "I couldn't verify the
specific facts behind 'how are you'".
"""

from __future__ import annotations

import re
from typing import Optional

# Word-level typo map, used ONLY for detection - the user's text is untouched.
_TYPOS = {
    "hw": "how", "r": "are", "u": "you", "ya": "you", "doin": "doing",
    "doin'": "doing", "wats": "whats", "wat": "what", "gud": "good",
    "mornin": "morning", "mornin'": "morning", "evnin": "evening",
    "thx": "thanks", "tx": "thanks", "ty": "thanks", "plz": "please",
    "sup": "whats up", "wassup": "whats up", "howdy": "hello",
    "hlo": "hello", "helo": "hello", "hiii": "hi", "hii": "hi",
    "gm": "good morning", "gn": "good night", "asalam": "salam",
}


def _norm(text: str) -> str:
    low = (text or "").lower().strip()
    low = re.sub(r"[^a-z0-9' ]+", " ", low)
    words = [_TYPOS.get(w, w) for w in low.split()]
    return " ".join(words)


_GREET = re.compile(
    r"^(?:hi|hey|hello|yo|hiya|howdy|greetings|good morning|good afternoon|"
    r"good evening|salam|salaam|assalam|assalamu alaikum|assalam o alaikum|"
    r"hi there|hello there|hey there|good day)\b", re.I)
_HOW = re.compile(
    r"\b(?:how are you|how r u|how are u|how's it going|hows it going|"
    r"how is it going|how do you do|how are you doing|whats up|what's up|"
    r"wassup|are you okay|are you ok|you good|how have you been)\b", re.I)
_THANKS = re.compile(r"^(?:thanks|thank you|thank u|thx|ty|much appreciated|"
                     r"thanks a lot|thank you so much|shukriya|jazakallah)\b", re.I)
_BYE = re.compile(r"^(?:bye|goodbye|byee|see you|see ya|take care|good night|"
                  r"cya|later|bye bye)\b", re.I)
_PRAISE = re.compile(r"\b(?:good job|well done|nice work|great answer|you are great|"
                     r"you're great|awesome|brilliant|perfect|well explained)\b", re.I)
_MOOD = re.compile(r"\b(?:i am bored|i'm bored|i feel bored|i am sad|i'm sad|"
                   r"i feel stuck|i am stuck|i'm tired|i am tired|i feel low)\b", re.I)
_TOD = [("good morning", "Good morning"), ("good afternoon", "Good afternoon"),
        ("good evening", "Good evening"), ("good night", "Good night")]


def _time_of_day(low: str) -> str:
    for needle, label in _TOD:
        if needle in low:
            return label
    return ""


def smalltalk(original: str, depth: str = "standard", name: str = "") -> Optional[str]:
    """Return a short, natural reply for small talk, else None (needs research)."""
    t = (original or "").strip()
    if not t or len(t) > 130:
        return None
    low = _norm(t)
    if not low:
        return None

    who = f", {name}" if name else ""
    tod = _time_of_day(low)
    kind = ""
    if _HOW.search(low):
        kind = "how"
    elif _GREET.match(low):
        kind = "greet"
    elif _THANKS.match(low):
        kind = "thanks"
    elif _BYE.match(low):
        kind = "bye"
    elif _PRAISE.search(low):
        kind = "praise"
    elif _MOOD.search(low):
        kind = "mood"
    if not kind:
        return None
    # "hi, write an email to my teacher" is a task, not a greeting. Thanks,
    # goodbyes and compliments still get their reply even if they mention work.
    if kind in ("greet", "how") and re.search(
            r"\b(?:capital|python|write|essay|email|letter|calculate|solve|explain|"
            r"what is|why is|how does|convert|define|story|poem|speech|report)\b", low):
        return None

    if kind == "how":
        head = f"{(tod + '! ') if tod else ''}I'm doing really well{who} - thanks for asking."
        out = ["## Hey!", "", head,
               "Everything is running smoothly on my side and I'm ready whenever you are. "
               "How is your day going?"]
    elif kind == "greet":
        opener = (tod + "!") if tod else "Hey!"
        out = ["## " + opener, "",
               f"Hi{who} - good to see you. I'm here and ready, no setup needed.",
               "Ask me anything at all, however you'd like to phrase it - a quick fact, a full "
               "explanation, a calculation, or something you need written."]
    elif kind == "thanks":
        out = ["## Anytime", "",
               f"You're very welcome{who}. Glad I could help - that is exactly what I'm here for.",
               "If you want to go deeper on the same thing, just say 'tell me more' and I'll keep the "
               "context from this chat."]
    elif kind == "bye":
        out = ["## See you", "",
               f"Take care{who}! I'll keep everything we discussed in this chat's memory, so you can "
               "pick up right where you left off.",
               "Come back whenever you like - I don't go anywhere."]
    elif kind == "praise":
        out = ["## Thank you!", "",
               f"That's kind of you{who} - I appreciate it. I'll keep holding to the same standard.",
               "If there's anything you'd like sharper, longer, shorter or in a different style, just "
               "say the word."]
    else:  # mood
        out = ["## I'm here", "",
               f"Thanks for telling me{who}. That sounds like a rough patch, and it's completely "
               "normal to hit one.",
               "If you want a distraction, I can write you a short story or a poem, tell you a clean "
               "joke, or walk through a small puzzle. If you'd rather just talk, that's fine too - "
               "I'm not going anywhere."]

    if depth != "quick":
        out += ["", "## A few things you can try right now", "",
                "- **Say hi properly:** 'how are you doing today?' - I'll actually answer it.",
                "- **Ask for a fact:** 'what is the capital of Japan?' - straight to the point.",
                "- **Ask me to write:** 'write an email to my teacher asking for leave', "
                "'write an essay on climate change', 'write a Python function that reverses a string'.",
                "- **Go deep:** pick Quick, Standard, Deep or Exhaustive in the top bar - I change "
                "both the answer and the accent colour."]
    if depth in ("deep", "exhaustive"):
        out += ["", "## A little about me", "",
                "I'm Ryzek AI, made by Rasakh Mohsin aka Ryzek. I answer every message - including "
                "the small-talk ones - with something useful rather than a shrug. I also remember "
                "your name, the facts you tell me and the topic we were discussing in this chat."]
    out += ["", "What's on your mind?"]
    return "\n".join(out)
