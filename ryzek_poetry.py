#!/usr/bin/env python3
"""
Ryzek AI v2.6.3 - poet-by-poet recital library.

Before this module, "tell me poetry of Ghalib" was answered as if it were a
question *about* Ghalib: historical paragraphs, no verse. This is the fix. A
poem library keyed by poet, holding short, widely-quoted excerpts with the
Urdu script, a Roman transliteration and an English rendering.

Why excerpts and not whole ghazals: a ghazal has seven to fifteen couplets
and several are still in copyright (Faiz died in 1984, Faraz in 2008, Jaun
Elia in 2002). Two or three couplets is the normal size of a quotation, it
stays inside fair use, and it is what a reader actually wants when they ask
"tell me some poetry".

Adding a poet is one entry in POETS - plain data, no logic.
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional

# ---------------------------------------------------------------------------
# the library
# ---------------------------------------------------------------------------
# urdu    : the verse in Urdu script
# roman   : transliteration, so it can be read aloud by someone who does not
#           read Urdu script
# english : plain-English meaning (a rendering, not a "translation")
# work    : the collection the lines come from, when it is known

POETS: Dict[str, Dict[str, Any]] = {
    "ghalib": {
        "title": "Mirza Ghalib",
        "urdu_name": "مرزا غالب",
        "dates": "1797-1869",
        "kind": "urdu",
        "about": "The most quoted poet in Urdu. He wrote in a Persian-heavy idiom, "
                 "filled with doubt, irony and metaphysical complaint, and made "
                 "ordinary conversation sound like philosophy.",
        "verses": [
            {
                "urdu": "ہزاروں خواہشیں ایسی کہ ہر خواہش پہ دم نکلے\n"
                        "بہت نکلے مرے ارمان لیکن پھر بھی کم نکلے",
                "roman": "hazāron khwāhishein aisī ke har khwāhish pe dam nikle\n"
                         "bahut nikle mere armān lekin phir bhī kam nikle",
                "english": "A thousand desires, each one enough to cost me my life. "
                           "Many of my longings were fulfilled - and still they were too few.",
                "work": "Diwan-e-Ghalib",
            },
            {
                "urdu": "دلِ ناداں تجھے ہوا کیا ہے\nآخر اس درد کی دوا کیا ہے",
                "roman": "dil-e-nādān tujhe huā kyā hai\nākhir is dard kī dawā kyā hai",
                "english": "Foolish heart, what has happened to you? After all, "
                           "what is the cure for this pain?",
                "work": "Diwan-e-Ghalib",
            },
            {
                "urdu": "بازیچۂ اطفال ہے دنیا مرے آگے\nہوتا ہے شب و روز تماشا مرے آگے",
                "roman": "bāzīcha-e-atfāl hai duniyā mere āge\nhotā hai shab-o-roz tamāshā mere āge",
                "english": "The world is a children's game before me; night and day "
                           "a spectacle unfolds in front of me.",
                "work": "Diwan-e-Ghalib",
            },
        ],
    },
    "iqbal": {
        "title": "Allama Muhammad Iqbal",
        "urdu_name": "علامہ محمد اقبال",
        "dates": "1877-1938",
        "kind": "urdu",
        "about": "Poet-philosopher of khudi (selfhood). His verse is exhortation: "
                 "it pushes the reader to become larger than circumstance.",
        "verses": [
            {
                "urdu": "ستاروں سے آگے جہاں اور بھی ہیں\n"
                        "ابھی عشق کے امتحاں اور بھی ہیں",
                "roman": "sitāron se āge jahān aur bhī hain\nabhī ishq ke imtihān aur bhī hain",
                "english": "There are worlds beyond the stars, and the trials of "
                           "love are not finished yet.",
                "work": "Bal-e-Jibril",
            },
            {
                "urdu": "خودی کو کر بلند اتنا کہ ہر تقدیر سے پہلے\n"
                        "خدا بندے سے خود پوچھے، بتا تیری رضا کیا ہے",
                "roman": "khudī ko kar buland itnā ke har taqdīr se pehle\n"
                         "khudā bande se khud pūchhe, batā terī razā kyā hai",
                "english": "Raise the self so high that, before every decree of fate, "
                           "God Himself asks the servant: tell me, what is your wish?",
                "work": "Bal-e-Jibril",
            },
        ],
    },
    "mir": {
        "title": "Mir Taqi Mir",
        "urdu_name": "میر تقی میر",
        "dates": "1723-1810",
        "kind": "urdu",
        "about": "The poet of grief and simplicity, and the first great chronicler "
                 "of Delhi's decline. Ghalib called him 'the master'.",
        "verses": [
            {
                "urdu": "پتا پتا بوٹا بوٹا حال ہمارا جانے ہے\n"
                        "جانے نہ جانے گل ہی نہ جانے، باغ تو سارا جانے ہے",
                "roman": "pattā pattā bootā bootā hāl hamārā jāne hai\n"
                         "jāne na jāne gul hī na jāne, bāgh to sārā jāne hai",
                "english": "Every leaf knows my condition, every sapling knows it. "
                           "The flower alone may not know - but the whole garden knows.",
                "work": "Kulliyat-e-Mir",
            },
            {
                "urdu": "میر کے دین و مذہب کو اب پوچھتے کیا ہو\n"
                        "اس نے تو دل جس کا ہے، اس کی ہی قسم کھائی ہے",
                "roman": "mīr ke dīn-o-mazhab ko ab pūchhte kyā ho\n"
                         "us ne to dil jis kā hai, us kī hī qasam khāī hai",
                "english": "Why ask now about Mir's faith? He swore by the one "
                           "who owns his heart, and that was his religion.",
                "work": "Kulliyat-e-Mir",
            },
        ],
    },
    "faiz": {
        "title": "Faiz Ahmed Faiz",
        "urdu_name": "فیض احمد فیض",
        "dates": "1911-1984",
        "kind": "urdu",
        "about": "Poet of the Progressive Writers' Movement: love and politics in "
                 "the same breath, and the most musical Urdu poet of the last century.",
        "verses": [
            {
                "urdu": "اور بھی دکھ ہیں زمانے میں محبت کے سوا\n"
                        "راحتیں اور بھی ہیں وصل کی راحت کے سوا",
                "roman": "aur bhī dukh hain zamāne mein mohabbat ke sivā\n"
                         "rāhaten aur bhī hain wasl kī rāhat ke sivā",
                "english": "There are other sorrows in this world besides love; "
                           "there are comforts other than the comfort of union.",
                "work": "Dast-e-Saba",
            },
            {
                "urdu": "ہم دیکھیں گے\nلازم ہے کہ ہم بھی دیکھیں گے",
                "roman": "hum dekhenge\nlāzim hai ke hum bhī dekhenge",
                "english": "We shall see. It is certain that we too shall see.",
                "work": "Hum Dekhenge, 1979",
            },
        ],
    },
    "faraz": {
        "title": "Ahmad Faraz",
        "urdu_name": "احمد فراز",
        "dates": "1931-2008",
        "kind": "urdu",
        "about": "The romantic who made Urdu poetry conversational again; his "
                 "couplets are the ones people actually quote to each other.",
        "verses": [
            {
                "urdu": "رنجش ہی سہی دل ہی دکھانے کے لیے آ\n"
                        "آ پھر سے مجھے چھوڑ کے جانے کے لیے آ",
                "roman": "ranjish hī sahī dil hī dukhāne ke liye ā\n"
                         "ā phir se mujhe chhoṛ ke jāne ke liye ā",
                "english": "Come, even if it is to quarrel - come just to hurt me. "
                           "Come again, even if only to leave me again.",
                "work": "Dard-e-Āshob",
            },
            {
                "urdu": "سلسلے توڑ گیا وہ سبھی جتنے تھے\n"
                        "اب کیا روئیں، جدائی کا سبب کیا کہیے",
                "roman": "silsile toṛ gayā wo sabhī jitne the\n"
                         "ab kyā ro'ein, judāī kā sabab kyā kahiye",
                "english": "He broke every thread there was. What is left to cry "
                           "about? What reason for parting should I even name?",
                "work": "Mīr-e-Kā'īnāt",
            },
        ],
    },
    "jaun-elia": {
        "title": "Jaun Elia",
        "urdu_name": "جون ایلیا",
        "dates": "1931-2002",
        "kind": "urdu",
        "about": "A deliberately difficult voice: exile, doubt and self-mockery, "
                 "written in a hard, new idiom that younger poets still copy.",
        "verses": [
            {
                "urdu": "تمہاری ہی تو نہیں ہے یہ گریہ و زاری\n"
                        "یہ شہر بھر کے ستاروں کا رونا ہے میں ہوں",
                "roman": "tumhārī hī to nahī hai ye girya-o-zārī\n"
                         "ye shahr bhar ke sitāron kā ronā hai, main hoon",
                "english": "This weeping is not yours alone - it is every lamp in "
                           "the city crying, and I am the one doing it.",
                "work": "Shāyad",
            },
        ],
    },
    "parveen-shakir": {
        "title": "Parveen Shakir",
        "urdu_name": "پروین شاکر",
        "dates": "1952-1994",
        "kind": "urdu",
        "about": "She wrote in a distinctly female first person and made the "
                 "ghazal admit everyday domestic detail.",
        "verses": [
            {
                "urdu": "وہ تو خوشبو ہے، ہواؤں میں بکھر جائے گا\n"
                        "مسئلہ پھول کا ہے، پھول کدھر جائے گا",
                "roman": "wo to khushbū hai, hawā'on mein bikhar jā'egā\n"
                         "mas'ala phool kā hai, phool kidhar jā'egā",
                "english": "He is a fragrance: it will scatter on the wind. The "
                           "real problem is the flower - where is the flower to go?",
                "work": "Khushbu",
            },
        ],
    },
    "dickinson": {
        "title": "Emily Dickinson",
        "urdu_name": "",
        "dates": "1830-1886",
        "kind": "english",
        "about": "Short lines, slant rhyme, enormous interior distance. She "
                 "published almost nothing in her lifetime.",
        "verses": [
            {
                "lines": "Hope is the thing with feathers\n"
                         "That perches in the soul,\n"
                         "And sings the tune without the words,\n"
                         "And never stops at all.",
                "english": "Hope as a small bird that keeps singing through the storm.",
                "work": "Poem 254, c. 1861",
            },
            {
                "lines": "Because I could not stop for Death -\n"
                         "He kindly stopped for me -\n"
                         "The Carriage held but just Ourselves -\n"
                         "And Immortality.",
                "english": "Death arrives as a courteous carriage ride, not as a terror.",
                "work": "Poem 712, c. 1863",
            },
        ],
    },
    "frost": {
        "title": "Robert Frost",
        "urdu_name": "",
        "dates": "1874-1963",
        "kind": "english",
        "about": "Plain New England speech carrying philosophical weight; metre "
                 "that sounds like conversation until you count the beats.",
        "verses": [
            {
                "lines": "The woods are lovely, dark and deep,\n"
                         "But I have promises to keep,\n"
                         "And miles to go before I sleep,\n"
                         "And miles to go before I sleep.",
                "english": "Duty pulling against stillness - the repetition is the whole poem.",
                "work": "Stopping by Woods on a Snowy Evening, 1923",
            },
            {
                "lines": "Two roads diverged in a wood, and I -\n"
                         "I took the one less traveled by,\n"
                         "And that has made all the difference.",
                "english": "The choice of a road, and the story we tell about it afterwards.",
                "work": "The Road Not Taken, 1916",
            },
        ],
    },
    "wordsworth": {
        "title": "William Wordsworth",
        "urdu_name": "",
        "dates": "1770-1850",
        "kind": "english",
        "about": "Romantic poet of memory and landscape; ordinary language raised "
                 "to the level of philosophy.",
        "verses": [
            {
                "lines": "I wandered lonely as a cloud\n"
                         "That floats on high o'er vales and hills,\n"
                         "When all at once I saw a crowd,\n"
                         "A host, of golden daffodils.",
                "english": "A walk, a field of daffodils, and the memory that later becomes wealth.",
                "work": "I Wandered Lonely as a Cloud, 1807",
            },
        ],
    },
    "keats": {
        "title": "John Keats",
        "urdu_name": "",
        "dates": "1795-1821",
        "kind": "english",
        "about": "Sensuous, almost edible language; died at 25 having already "
                 "written the odes that define English lyric poetry.",
        "verses": [
            {
                "lines": "Beauty is truth, truth beauty, - that is all\n"
                         "Ye know on earth, and all ye need to know.",
                "english": "The closing claim of the Grecian Urn ode: beauty and truth as one thing.",
                "work": "Ode on a Grecian Urn, 1819",
            },
        ],
    },
    "shakepeare": {
        "title": "William Shakespeare",
        "urdu_name": "",
        "dates": "1564-1616",
        "kind": "english",
        "about": "Sonnets that invented the modern idea of romantic inwardness in "
                 "English poetry.",
        "verses": [
            {
                "lines": "Shall I compare thee to a summer's day?\n"
                         "Thou art more lovely and more temperate:",
                "english": "The most quoted opening in English love poetry.",
                "work": "Sonnet 18, 1609",
            },
        ],
    },
}

# alternate names -> library key
ALIASES = {
    "ghalib": "ghalib", "mirza ghalib": "ghalib", "mirza asadullah khan ghalib": "ghalib",
    "asadullah khan ghalib": "ghalib",
    "iqbal": "iqbal", "allama iqbal": "iqbal", "allama muhammad iqbal": "iqbal",
    "sir iqbal": "iqbal", "muhammad iqbal": "iqbal",
    "mir": "mir", "mir taqi mir": "mir", "mirza taqi mir": "mir",
    "faiz": "faiz", "faiz ahmed faiz": "faiz", "faiz ahmad faiz": "faiz",
    "faraz": "faraz", "ahmad faraz": "faraz", "ahmed faraz": "faraz",
    "jaun elia": "jaun-elia", "jaun": "jaun-elia", "john elia": "jaun-elia",
    "parveen shakir": "parveen-shakir", "parvin shakir": "parveen-shakir",
    "dickinson": "dickinson", "emily dickinson": "dickinson",
    "frost": "frost", "robert frost": "frost",
    "wordsworth": "wordsworth", "william wordsworth": "wordsworth",
    "keats": "keats", "john keats": "keats",
    "shakespeare": "shakepeare", "william shakespeare": "shakepeare",
}

POETRY_WORDS = re.compile(
    r"\b(poem|poetry|poet|verse|verses|couplet|couplets|ghazal|ghazals|shayari|shairi|"
    r"shero?|sher|nazm|rubai|bait|baitain|recite|recitation|quote me|qalaam|kalam)\b", re.I)

OF_BY = re.compile(
    r"\b(?:of|by|from|ka|ki|kalam|qalaam|koi|some)\b", re.I)

# poets whose verse is in Urdu script
URDU_KEYS = {k for k, v in POETS.items() if v["kind"] == "urdu"}


def find_poet(text: str) -> Optional[str]:
    """Return a library key when the text names a poet we carry verses for."""
    low = " " + re.sub(r"[^\w\s-]", " ", (text or "").lower()) + " "
    # longest alias first so "mir taqi mir" beats "mir"
    for alias in sorted(ALIASES, key=len, reverse=True):
        if " " + alias + " " in low:
            return ALIASES[alias]
    return None


_DEFINITION = re.compile(
    r"^\s*(what|who)\s+(is|are|was|were)\b|\b(definition|meaning of|history of|"
    r"types of|forms of|difference between)\b", re.I)


def wants_poetry(text: str) -> bool:
    """True for 'tell me poetry of X', 'recite a ghazal by Y', 'X ki shayari'."""
    t = text or ""
    if not POETRY_WORDS.search(t):
        return False
    if _DEFINITION.search(t):
        return False                      # 'what is a ghazal?' is a knowledge question
    # 'write a poem about rain' is a writing job; 'write a poem like Faiz' or
    # 'give me a poem by Dickinson' is asking for the poet's own verse.
    if re.search(r"\b(write|compose|create|make|draft|generate|likho|likh)\b", t, re.I):
        if not re.search(r"\b(like|of|by|in the style|style of|ki tarah|jaisi|jaisa)\b",
                         t, re.I):
            return False
    # a poem *by* a poet means their verse; a poem *about* a poet is a job
    if re.search(r"\b(about|on|for me|mere baare)\b", t, re.I):
        return False
    return True


def wants_urdu_script(text: str) -> bool:
    if re.search(r"[\u0600-\u06FF]", text or ""):
        return True
    return bool(re.search(r"\b(urdu|urdu mein|roman|transliterat|english meaning|tarjuma)\b",
                          text or "", re.I))


def _verse_block(p: Dict[str, Any], v: Dict[str, Any], index: int) -> List[str]:
    out: List[str] = []
    if p["kind"] == "urdu":
        # dir hint picked up by the renderer: RTL + a Nastaliq face
        out.append(':::urdu')
        out.append(v["urdu"])
        out.append(':::')
        out.append("")
        # each transliteration line is its own italic run, separated by a hard break
        roman = [ln.strip() for ln in v["roman"].split("\n") if ln.strip()]
        out.append("  \n".join("*" + ln + "*" for ln in roman))
    else:
        out.append("> " + v["lines"].replace("\n", "\n> "))
    out.append("")
    out.append(f"**In plain English:** {v['english']}")
    if v.get("work"):
        out.append("")
        out.append(f"*Source: {v['work']}.*")
    return out


def recite(poet_key: str, question: str = "") -> str:
    """Build a recital answer for a poet in the library."""
    p = POETS[poet_key]
    script = wants_urdu_script(question)
    verses = p["verses"]
    if not script and p["kind"] == "urdu":
        # asked in English without asking for the script: still show it, it is
        # the poem; but lead with the meaning-heavy framing
        pass

    lines: List[str] = []
    title = p["title"]
    if p.get("urdu_name"):
        title = f"{p['title']} ({p['urdu_name']})"
    lines.append(f"# {title}")
    lines.append("")
    if p.get("dates"):
        lines.append(f"*{p['dates']}*")
        lines.append("")
    lines.append(p["about"])
    lines.append("")

    shown = verses[:2] if len(verses) > 1 else verses
    for i, v in enumerate(shown):
        lines.append(f"## {'A couplet' if p['kind'] == 'urdu' else 'The lines'}"
                     + (f" {i + 1}" if len(shown) > 1 else ""))
        lines.append("")
        lines.extend(_verse_block(p, v, i))
        lines.append("")

    if len(verses) > len(shown):
        lines.append(f"*Ask me for more and I will give you another "
                     f"{'couplet' if p['kind'] == 'urdu' else 'poem'} from {p['title'].split()[-1]}.*")
        lines.append("")

    if p["kind"] == "urdu":
        lines.append("## How to read it")
        lines.append("")
        lines.append("The first line is the script, the second is how it sounds, and "
                     "the third is the meaning. Read the transliteration out loud - a "
                     "ghazal is built to be heard, and the sound carries meaning that a "
                     "literal translation loses.")
        lines.append("")
        lines.append("*These are short, widely quoted excerpts, included for reading and "
                     "study. Nothing here is a complete ghazal.*")
    else:
        lines.append("## Why it matters")
        lines.append("")
        lines.append("Read it once for the sound, once for the sense. The pause at the "
                     "line break is part of the meaning: English metre makes you wait "
                     "half a beat exactly where the thought turns.")
    return "\n".join(lines)


def material_for(poet_key: str) -> List[str]:
    """Lines usable as research material (kept short; core only needs keywords)."""
    p = POETS[poet_key]
    out = [p["about"]]
    for v in p["verses"]:
        out.append(v["english"])
        if v.get("work"):
            out.append(f"From {v['work']}.")
    return out


def list_poets() -> str:
    urdu = [POETS[k]["title"] for k in POETS if POETS[k]["kind"] == "urdu"]
    eng = [POETS[k]["title"] for k in POETS if POETS[k]["kind"] == "english"]
    return ("I can recite from memory: " + ", ".join(urdu) + ". "
            "In English: " + ", ".join(eng) + ". "
            "Ask for any of them by name - for example \"tell me poetry of Ghalib\".")


def count() -> int:
    return sum(len(p["verses"]) for p in POETS.values())
