#!/usr/bin/env python3
"""
Ryzek AI - safety guardrails.

The standing rule is that every message gets a substantive answer. A safety
refusal is still an answer: it clearly declines the harmful part, explains the
boundary briefly, and offers a concrete, safe alternative. It never supplies
procedural steps for harm.

Patterns are deliberately narrow and intent-based ("how to make/build/hack")
so benign questions - history of the atomic bomb, killing a stuck Python
process, securing a Wi-Fi network, how viruses work - are never blocked.
"""

from __future__ import annotations

import re
from typing import Optional, Tuple

RULES = [
    (
        "self-harm",
        re.compile(r"\b(?:kill myself|hurt myself|end my life|suicide|self[-\s]?harm|"
                   r"cut myself|how (?:do|to|can) i (?:kill|hurt|harm) myself|"
                   r"i want to die|ways to die)\b", re.I),
        "There is support available, and you deserve to talk to a real person right now.",
        [
            "If you might act on these thoughts, please contact your local emergency number, "
            "go to the nearest emergency department, or call a crisis line in your country.",
            "Reach out to one person you trust - a friend, a family member, a teacher or a "
            "doctor - and tell them plainly how you are feeling.",
            "If you are asking on behalf of someone else, stay with them and help them contact "
            "a qualified professional.",
            "I can also help with calm, non-clinical things: grounding exercises, a short "
            "message you could send to someone, or simply a quiet, judgement-free conversation.",
        ],
    ),
    (
        "weapons or explosives",
        re.compile(r"\b(?:how (?:do|to|can) (?:i|we|you) (?:make|build|create|construct|assemble|"
                   r"synthesize|synthesise) (?:a|an|the)?\s*(?:bomb|explosive|ied|gun|firearm|"
                   r"weapon|poison|nuclear|chemical weapon|biological weapon)|"
                   r"instructions (?:for|to) (?:make|build) (?:a|an)?\s*(?:bomb|explosive)|"
                   r"build a bomb at home|make a bomb at home)\b", re.I),
        "Building weapons, explosives or poisons can cause irreversible harm and is illegal in "
        "most places, so I will not provide instructions, materials or steps.",
        [
            "I can explain the underlying science at a safe, conceptual level - for example how "
            "combustion, pressure waves or nuclear fission work in a textbook context.",
            "I can discuss the history and policy of arms control, or the chemistry of energetic "
            "reactions without any practical recipe.",
            "If you found or are handling a suspicious object, do not touch it; move away and "
            "contact local emergency services.",
            "If this is for fiction, research or a game, tell me the scene and I can help with "
            "realistic-feeling description that contains no usable procedure.",
        ],
    ),
    (
        "illegal drugs",
        re.compile(r"\b(?:how (?:do|to|can) (?:i|we|you) (?:make|synthesize|synthesise|cook|"
                   r"manufacture|produce) (?:meth|methamphetamine|heroin|cocaine|fentanyl|mdma|"
                   r"crack cocaine)|recipe for (?:meth|heroin|cocaine|fentanyl))\b", re.I),
        "Manufacturing controlled substances is dangerous and illegal, so I will not give a "
        "recipe, a precursor list or procedural steps.",
        [
            "I can explain the pharmacology of how substances affect the body at a general "
            "educational level, or the public-health reasoning behind drug scheduling.",
            "If you or someone close to you is struggling with substance use, a doctor or a "
            "local support service can help far better than I can.",
            "For a chemistry assignment, I can help with safe, legal laboratory concepts instead.",
        ],
    ),
    (
        "unauthorised access or malware",
        re.compile(r"(?:\bhow (?:do|to|can|could|would) (?:i|we|you)\b|\bhelp me\b|"
                   r"\bshow me how to\b|\bgive me (?:a|the)? ?(?:way|steps|code) to\b|"
                   r"\bwrite (?:a|an)? ?(?:script|code|program) to\b)"
                   r".{0,120}?\b(?:hack|crack|break into|spy on|steal|bypass|ddd?os)\b"
                   r".{0,120}?\b(?:wifi|wi-fi|instagram|facebook|whatsapp|account|password|"
                   r"phone|email|e-mail|computer|bank|server|network|website)\b"
                   r"|\bwrite (?:a|an)?\s*(?:keylogger|virus|ransomware|malware|botnet)\b"
                   r"|\b(?:ddos|denial of service) attack (?:on|against)\b"
                   r"|\bbypass (?:someone's|his|her|their|a|the) password\b", re.I),
        "Accessing accounts, devices or networks without permission is illegal and harms real "
        "people, so I will not give steps, code or tooling for it.",
        [
            "I can help you secure your own accounts: strong unique passwords, a password "
            "manager, two-factor authentication and recovery codes.",
            "I can explain how phishing, credential stuffing or SQL injection work at a "
            "defensive, conceptual level so you can recognise them.",
            "If you lost access to your own account, use the provider's official recovery flow.",
            "If you found a vulnerability, I can help you write a responsible-disclosure report.",
        ],
    ),
    (
        "violence against a person",
        re.compile(r"\b(?:how (?:do|to|can) (?:i|we|you) (?:kill|murder|hurt|attack|poison|"
                   r"assault|injure) (?:someone|a person|my (?:neighbour|neighbor|friend|partner|"
                   r"wife|husband|boss|teacher|classmate))|"
                   r"best way to (?:kill|hurt|attack) (?:someone|a person))\b", re.I),
        "I will not help plan or carry out harm against another person.",
        [
            "If you are angry or frightened and someone may be in danger, put distance between "
            "you and them and contact local emergency services or someone you trust.",
            "Conflict de-escalation, mediation and safe exit planning are all things I can help "
            "you think through in detail.",
            "If this is a hypothetical for a story or a debate, tell me the framing and I can "
            "discuss the ethics or write non-actionable narrative.",
        ],
    ),
    (
        "fraud or forgery",
        re.compile(r"\b(?:how (?:do|to|can) (?:i|we|you) (?:forge|counterfeit|fake) "
                   r"(?:money|currency|a passport|an id|a document|a certificate)|"
                   r"make fake (?:money|passport|id|documents))\b", re.I),
        "Forgery and counterfeiting are crimes that harm real people, so I will not provide "
        "methods or templates.",
        [
            "I can explain how document security features work conceptually, which is useful for "
            "designing legitimate verification checks.",
            "If you lost a document, I can outline the normal replacement process for you to "
            "confirm with the issuing authority.",
        ],
    ),
    (
        "religious mockery",
        re.compile(r"\b(?:write|make|give me|tell me|create|generate)\b.{0,70}"
                   r"\b(?:insult\w*|mock\w*|make fun of|offensive|disrespect\w*|derogatory|"
                   r"hateful|rude)\b.{0,70}\b(?:prophet\w*|religion\w*|scripture\w*|god|allah|"
                   r"quran|bible|islam|christian\w*|jew\w*|hindu\w*|muslim\w*)\b", re.I),
        "I treat prophets, Scriptures and every faith with courtesy, so I will not produce "
        "insulting or mocking material about them.",
        [
            "I can give a neutral, well-sourced explanation of the tradition you are asking about.",
            "I can explain why certain imagery is sacred or sensitive to believers, which is "
            "genuinely useful context for writing or research.",
            "I can help you rephrase a question so it is comparative, historical or analytical "
            "rather than disparaging - and then answer it thoroughly.",
        ],
    ),
]


def check(text: str) -> Optional[str]:
    """Return a safe, substantive response, or None if the request is benign."""
    low = text or ""
    for category, pattern, reason, alternatives in RULES:
        if not pattern.search(low):
            continue
        out = ["## I can't help with that part", "",
               reason + " That is a firm boundary, not an evasion - and I am still giving you a "
               "useful answer here."]
        if category == "self-harm":
            out += ["", "## Please reach out", "",
                    "You matter, and this situation can change. The safest next step is a real "
                    "human conversation, not a chatbot."]
        out += ["", "## What I can do instead", ""] + [f"- {a}" for a in alternatives]
        out += ["", "## Why I drew the line", "",
                "My rule is that every message gets a substantive reply, but 'substantive' never "
                "means actionable instructions for serious harm. Declining the harmful part while "
                "answering the safe part is the honest version of helpfulness.", "",
                "## Keep going", "",
                "Ask me the safe version of your question and I will answer it in full detail, "
                "with sources and worked reasoning."]
        return "\n".join(out)
    return None


# Quick self-check helpers for tests / diagnostics.
def classify(text: str) -> Tuple[str, bool]:
    for category, pattern, *_ in RULES:
        if pattern.search(text or ""):
            return category, True
    return "", False
