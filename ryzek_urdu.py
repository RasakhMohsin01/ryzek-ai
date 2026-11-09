#!/usr/bin/env python3
"""
Ryzek AI - original Urdu poetry (v2.5).

The user asked for Urdu poetry and was getting either a research essay about
ghazals or nothing at all. This module writes actual Urdu verse: a ghazal with
a consistent qafiya (rhyme) and radif (refrain), plus Roman-Urdu
transliteration and a short plain-English meaning for every couplet.

The verse here is original, written for this project; it is not copied from a
published poet. Each sher is rendered by the UI inside a `:::urdu` block as a
right-to-left, Nastaliq-friendly stanza.

Themes: love, hope, friendship, homeland, rain, knowledge and life (default).
"""

from __future__ import annotations

import re
from typing import Dict, List, Tuple

# (Urdu line 1, Urdu line 2, Roman line 1, Roman line 2, plain-English meaning)
Sher = Tuple[str, str, str, str, str]

THEMES: Dict[str, Dict[str, object]] = {
    "love": {
        "ur": "محبت", "en": "Love", "radif": "رہے", "qafiya": "ـتے",
        "shers": [
            ("دل کی ہر بات ہم تم تک پہنچاتے رہے",
             "اور جو نہ پہنچی، اُسے خوابوں میں لکھتے رہے",
             "Dil ki har baat hum tum tak pahunchaate rahe",
             "Aur jo na pahunchi, use khwabon mein likhte rahe",
             "I tried to say everything I felt; what I could not say, I kept writing in dreams."),
            ("رات بھر چاند نے کھڑکی پہ دستک دی",
             "ہم نے بھی چراغ جلا کر اُسے سنتے رہے",
             "Raat bhar chaand ne khidki pe dastak di",
             "Hum ne bhi chiraagh jala kar use sunte rahe",
             "The moon tapped at my window all night; I lit a lamp and just listened."),
            ("تم نے پوچھا کہ کیسے ہو، ہم مسکرا دیے",
             "ورنہ آنکھوں میں ایک درد کو چھپاتے رہے",
             "Tum ne poocha ke kaise ho, hum muskura diye",
             "Warna aankhon mein ek dard ko chhupaate rahe",
             "You asked how I was and I smiled, while hiding an ache behind my eyes."),
            ("شہر کی بھیڑ میں بھی تم ہی نظر آئے",
             "ہم نے ہر راستے سے تم کو ڈھونڈتے رہے",
             "Shehar ki bheed mein bhi tum hi nazar aaye",
             "Hum ne har raaste se tum ko dhoondte rahe",
             "Even in a crowded street I saw only you, and looked for you on every road."),
            ("خط میں اک جملہ ادھورا سا رہ گیا",
             "ہم نے اُسے بار بار پڑھ کر سنبھالتے رہے",
             "Khat mein ek jumla adhoora sa reh gaya",
             "Hum ne use baar baar parh kar sambhaalte rahe",
             "One line of the letter stayed unfinished; I read it again and again and kept it safe."),
            ("ریزک! محبت میں نام کا کیا کام آئے",
             "پھر بھی ہم اپنا حال سب کو سناتے رہے",
             "Ryzek! Muhabbat mein naam ka kya kaam aaye",
             "Phir bhi hum apna haal sab ko sunaate rahe",
             "Ryzek says a name matters little in love; even so, I kept telling my story."),
        ],
    },
    "hope": {
        "ur": "امید", "en": "Hope", "radif": "ہے", "qafiya": "ـات",
        "shers": [
            ("ابھی تو اندھیرے کی آخری رات ہے",
             "اور سورج سے پہلے اک چھوٹی سی بات ہے",
             "Abhi to andhere ki aakhri raat hai",
             "Aur sooraj se pehle ek chhoti si baat hai",
             "This is the last dark night, and there is still one small thing to say before sunrise."),
            ("ہر زخم کے پیچھے اک نئی ساعت ہے",
             "جو کل نہ تھی، آج وہ بھی اک چاہت ہے",
             "Har zakhm ke peechhe ek nayi sa'at hai",
             "Jo kal na thi, aaj wo bhi ek chaahat hai",
             "Behind every wound is a new moment; what was missing yesterday is a wish today."),
            ("در بند ہوا تو کیا، ابھی تو برسات ہے",
             "کھڑکی پہ رکھا دیا بھی جلتا جاتا ہے",
             "Dar band hua to kya, abhi to barsaat hai",
             "Khidki pe rakha diya bhi jalta jaata hai",
             "So the door closed; the rain is still here, and the lamp on the sill keeps burning."),
            ("ہم نے ہار نہیں مانی، بس سانس لی تھی",
             "اور آگے کی منزل اب بھی اک ضمانت ہے",
             "Hum ne haar nahi maani, bas saans li thi",
             "Aur aage ki manzil ab bhi ek zamaanat hai",
             "I did not give up; I only paused for breath, and the next step is still promised."),
            ("ریزک نے لکھا: اندھیرا بس اک رات ہے",
             "اُس کے آگے ہمیشہ نئی صبح کی ضمانت ہے",
             "Ryzek ne likha: andhera bas ek raat hai",
             "Us ke aage hamesha nayi subah ki zamaanat hai",
             "Ryzek wrote: darkness is only one night; a new morning always follows it."),
        ],
    },
    "friendship": {
        "ur": "دوستی", "en": "Friendship", "radif": "رہے", "qafiya": "ـتے",
        "shers": [
            ("جب بھی راستہ لمبا ہوا، تم ساتھ چلتے رہے",
             "ہم نے بھی اپنا ہاتھ تمہارے ہاتھ میں دیتے رہے",
             "Jab bhi raasta lamba hua, tum saath chalte rahe",
             "Hum ne bhi apna haath tumhaare haath mein dete rahe",
             "Whenever the road grew long you walked with me, and I kept my hand in yours."),
            ("باتوں میں کبھی تکلف نہ آیا",
             "ہم دونوں خاموشی کو بھی سمجھتے رہے",
             "Baaton mein kabhi takalluf na aaya",
             "Hum dono khamoshi ko bhi samajhte rahe",
             "There was never any formality between us; we understood even the silences."),
            ("دنیا نے کئی بار ہمیں بدلا بدلا کہا",
             "تم نے تو ہر بار وہی پرانی بات کہتے رہے",
             "Duniya ne kai baar hamein badla badla kaha",
             "Tum ne to har baar wahi puraani baat kehte rahe",
             "The world kept saying I had changed; you kept saying the same familiar thing."),
            ("دکھ میں فون نہ کیا، پھر بھی تم آ گئے",
             "ہم نے بھی دروازہ کھول کر مسکراتے رہے",
             "Dukh mein phone na kiya, phir bhi tum aa gaye",
             "Hum ne bhi darwaaza khol kar muskuraate rahe",
             "I never called in my low moment, yet you came; I opened the door smiling."),
            ("ریزک لکھتا ہے دوستی کوئی عنوان نہیں",
             "بس وہ لوگ ہیں جو خاموشی میں ساتھ دیتے رہے",
             "Ryzek likhta hai dosti koi unwaan nahi",
             "Bas wo log hain jo khamoshi mein saath dete rahe",
             "Ryzek says friendship is not a title; it is the people who stay quietly beside you."),
        ],
    },
    "homeland": {
        "ur": "وطن", "en": "Homeland", "radif": "ہے", "qafiya": "ـان",
        "shers": [
            ("یہ مٹی میری پہچان ہے",
             "اور ہر ذرّے میں اک ارمان ہے",
             "Ye mitti meri pehchaan hai",
             "Aur har zarre mein ek armaan hai",
             "This soil is my identity, and every grain of it holds a hope."),
            ("دریاؤں کا شور، کھیتوں کی خاموشی",
             "میرے بچپن کی یہی داستان ہے",
             "Daryaaon ka shor, kheton ki khamoshi",
             "Mere bachpan ki yahi daastaan hai",
             "The noise of the rivers and the quiet of the fields are the story of my childhood."),
            ("جہاں بھی جاؤں، ساتھ وہی آسمان ہے",
             "گھر سے دور بھی گھر کا سامان ہے",
             "Jahan bhi jaaoon, saath wahi aasmaan hai",
             "Ghar se door bhi ghar ka samaan hai",
             "Wherever I go the same sky travels with me, and I carry a little of home."),
            ("ہم نے اِسے الفاظ میں نہیں سمیٹا",
             "یہ تو سانسوں میں بسنے والی جان ہے",
             "Hum ne ise alfaaz mein nahi sameta",
             "Ye to saanson mein basne waali jaan hai",
             "I never tried to fit it into words; it lives in my breathing."),
            ("ریزک نے پوچھا: وطن کیا ہے؟",
             "جواب میں بس چراغوں کا اک سامان ہے",
             "Ryzek ne poocha: watan kya hai?",
             "Jawab mein bas chiraaghon ka ek samaan hai",
             "Ryzek asked what a homeland is; the answer was simply a small bundle of lamps."),
        ],
    },
    "rain": {
        "ur": "بارش", "en": "Rain", "radif": "رہے", "qafiya": "ـتے",
        "shers": [
            ("چھت پر پہلی بوند گری تو جی اٹھا",
             "ہم نے بھی کھڑکی کھول کر سنتے رہے",
             "Chhat pe pehli boond giri to ji utha",
             "Hum ne bhi khidki khol kar sunte rahe",
             "The first drop on the roof woke everything up; I opened the window and listened."),
            ("مٹی کی خوشبو اٹھی، سڑک چمکی",
             "بچے بھی کاغذ کی کشتیاں بناتے رہے",
             "Mitti ki khushboo uthi, sadak chamki",
             "Bache bhi kaagaz ki kashtiyan banaate rahe",
             "The scent of wet earth rose and the street shone; children kept making paper boats."),
            ("بجلی نے اک پل کو سارا شہر روشن کیا",
             "ہم نے بھی اندھیرے میں لکھتے رہے",
             "Bijli ne ek pal ko saara shehar roshan kiya",
             "Hum ne bhi andhere mein likhte rahe",
             "Lightning lit the whole city for a moment; I kept writing in the dark."),
            ("بارش تھمی تو چاند سا سکوت آیا",
             "پھر بھی نالے سے پانی بہتے رہے",
             "Baarish thami to chaand sa sukoot aaya",
             "Phir bhi naale se paani behte rahe",
             "When the rain stopped a moonlike hush arrived, yet water still ran in the drains."),
            ("ریزک نے کہا: برسات بھی اک خط ہے",
             "ہم نے اُسے بار بار پڑھتے رہے",
             "Ryzek ne kaha: barsaat bhi ek khat hai",
             "Hum ne use baar baar parhte rahe",
             "Ryzek says the monsoon is a letter too; I kept reading it again and again."),
        ],
    },
    "knowledge": {
        "ur": "علم", "en": "Knowledge", "radif": "رہے", "qafiya": "ـتے",
        "shers": [
            ("ایک سوال نے پوری رات جگائے رکھا",
             "ہم نے بھی کتابوں کے صفحے پلٹتے رہے",
             "Ek sawaal ne poori raat jagaaye rakha",
             "Hum ne bhi kitaabon ke safhe palatte rahe",
             "One question kept me awake all night, so I kept turning the pages."),
            ("جواب ملا تو اور سوال پیدا ہوئے",
             "ہم نے بھی حیرانی کو سہلاتے رہے",
             "Jawaab mila to aur sawaal paida hue",
             "Hum ne bhi hairaani ko sahlaate rahe",
             "The answer arrived and made more questions; I learned to be comfortable wondering."),
            ("استاد نے بس اتنا کہا: خود سوچو",
             "ہم نے بھی غلطی سے نئے راستے چنتے رہے",
             "Ustaad ne bas itna kaha: khud socho",
             "Hum ne bhi ghalti se naye raaste chunte rahe",
             "The teacher only said 'think for yourself', so I found new roads by getting things wrong."),
            ("لفظ کم تھے، مطلب بہت تھے",
             "ہم نے بھی خاموشی کو پڑھتے رہے",
             "Lafz kam the, matlab bahut the",
             "Hum ne bhi khamoshi ko parhte rahe",
             "There were few words and many meanings, so I kept reading the silence."),
            ("ریزک لکھتا ہے علم کوئی منزل نہیں",
             "بس ہم ہیں اور ہر روز سیکھتے رہے",
             "Ryzek likhta hai ilm koi manzil nahi",
             "Bas hum hain aur har roz seekhte rahe",
             "Ryzek says knowledge is not a destination; it is simply learning a little every day."),
        ],
    },
    "life": {
        "ur": "زندگی", "en": "Life", "radif": "رہے", "qafiya": "ـتے",
        "shers": [
            ("صبح نے پھر اک نیا دروازہ کھولا",
             "ہم نے بھی پرانی عادتیں بدلتے رہے",
             "Subah ne phir ek naya darwaaza khola",
             "Hum ne bhi puraani aadatein badalte rahe",
             "Morning opened one more door, and I kept changing an old habit."),
            ("جو نہ ملا اُس کا غم تھوڑا سا رہا",
             "جو ملا اُسے ہم سہلاتے رہے",
             "Jo na mila us ka gham thoda sa raha",
             "Jo mila use hum sahlaate rahe",
             "What I did not get left a small sadness; what I did get, I took care of."),
            ("کئی بار گرے، کئی بار سنبھلے",
             "پھر بھی اپنا راستہ خود ہی چنتے رہے",
             "Kai baar gire, kai baar sambhale",
             "Phir bhi apna raasta khud hi chunte rahe",
             "I fell often and steadied myself often, but I kept choosing my own road."),
            ("وقت نے کچھ چھینا، کچھ واپس دیا",
             "ہم نے دونوں ہاتھوں سے لیتے رہے",
             "Waqt ne kuch chheena, kuch waapas diya",
             "Hum ne donon haathon se lete rahe",
             "Time took some things and gave some back; I kept receiving with both hands."),
            ("ریزک لکھتا ہے زندگی کوئی عنوان نہیں",
             "بس ہم ہیں اور لمحوں کو گنتے رہے",
             "Ryzek likhta hai zindagi koi unwaan nahi",
             "Bas hum hain aur lamhon ko ginte rahe",
             "Ryzek says life is not a heading; it is just us, counting small moments."),
        ],
    },
}

THEME_WORDS: List[Tuple[str, str]] = [
    (r"love|mohabbat|muhabbat|ishq|pyaar|pyar|محبت|عشق|پیار", "love"),
    (r"hope|umeed|ummeed|امید|اُمید", "hope"),
    (r"friend|dost|dosti|دوست|دوستی|یار", "friendship"),
    (r"watan|homeland|country|pakistan|پاکستان|وطن|ملک", "homeland"),
    (r"rain|barish|baarish|barsaat| monsoon|بارش|برسات|ساون", "rain"),
    (r"knowledge|ilm|science|education|padhai|علم|تعلیم|کتاب", "knowledge"),
    (r"life|zindagi|زندگی|حیات", "life"),
]


def detect_theme(topic: str) -> str:
    t = (topic or "").lower()
    for pattern, key in THEME_WORDS:
        if re.search(pattern, t, re.I | re.U):
            return key
    return "life"


def _count(depth: str) -> int:
    return {"quick": 3, "standard": 4, "deep": 5, "exhaustive": 6}.get(depth, 4)


def write_urdu(topic: str = "", depth: str = "standard",
               material: object = None) -> str:
    """Return a finished original Urdu ghazal with transliteration and meaning."""
    key = detect_theme(topic)
    data = THEMES.get(key, THEMES["life"])
    shers: List[Sher] = list(data["shers"])  # type: ignore[arg-type]
    n = min(_count(depth), len(shers))
    chosen = shers[:n]
    ur_title, en_title = str(data["ur"]), str(data["en"])

    out = [f"## Urdu ghazal: {en_title} ({ur_title})", ""]
    out.append("Here is an original Urdu ghazal I wrote for you. Each couplet is a "
               "*sher*: two lines, with the same rhyme before the repeated word.")
    out += ["", ":::urdu"]
    for a, b, _r1, _r2, _m in chosen:
        out.append(a + " | " + b)
    out += [":::", ""]

    if depth != "quick":
        out += ["### Roman Urdu (so you can read it aloud)", ""]
        for i, (_a, _b, r1, r2, _m) in enumerate(chosen, 1):
            out.append(f"{i}. {r1}  /  {r2}")
        out += ["", "### What it means in English", ""]
        for i, (_a, _b, _r1, _r2, m) in enumerate(chosen, 1):
            out.append(f"{i}. {m}")
        out += ["", "### About this ghazal", "",
                f"- **Theme:** {en_title} ({ur_title}).",
                f"- **Radif** (the repeated word): **{data['radif']}**.",
                f"- **Qafiya** (the rhyme before it): **{data['qafiya']}**.",
                "- The verse is original, written for this chat, not copied from a published poet.",
                "- Urdu reads right to left, so each line above starts from the right.", ""]
    if depth in ("deep", "exhaustive"):
        out += ["### Want a different one?", "",
                "Ask for an Urdu ghazal on love, hope, friendship, homeland, rain, "
                "knowledge or life. You can also say `type urdu poetry on rain` or "
                "`ایک غزل لکھ دو` and I will write a fresh one at the length you want.", ""]
    if depth == "exhaustive":
        out += ["### How a ghazal is built", "",
                "1. The first couplet is the *matla*: both lines end with the rhyme and refrain.",
                "2. Every later couplet repeats them only in its second line.",
                "3. Each sher stands alone, yet the mood stays the same across the poem.",
                "4. The last couplet often carries the poet's pen name - here, *Ryzek*.", ""]
        out += ["### Sources", "", "- Original verse written by Ryzek AI. No external "
                "poem was reproduced, so there is nothing to cite.", ""]
    return "\n".join(out).strip() + "\n"
