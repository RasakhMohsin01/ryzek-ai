#!/usr/bin/env python3
"""
Ryzek AI v2.6 - curated everyday knowledge.

The knowledge base has 58 deep topics (physics, biology, history, ...), but the
questions people actually type are often everyday ones: "why does my phone
battery drain fast", "how do I get better at coding", "affect vs effect".

This module supplies short, checked, plainly-worded answers for those, keyed by
topic. It is deliberately small and honest: each entry is a paragraph or a list,
not a pretend encyclopaedia. The understanding layer picks the entry, the
answer kit wraps it in the right shape, and live web results add anything newer.

Entries are plain tuples so they stay easy to review and extend:

    "id": {"title": ..., "keys": [search words], "what": "...",
           "why": "...", "fix": [...], "note": "..."}
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional


def _e(title: str, keys: List[str], what: str, why: str = "",
       fix: Optional[List[str]] = None, note: str = "",
       facts: Optional[List[str]] = None) -> Dict[str, Any]:
    return {"title": title, "keys": keys, "what": what, "why": why,
            "fix": fix or [], "note": note, "facts": facts or []}


EVERYDAY: List[Dict[str, Any]] = [
    # ------------------------------------------------------------ why is it so
    _e("Why the sky is blue",
       ["sky is blue", "sky blue", "blue sky", "rayleigh", "why is sky", "sky color",
        "sky colour", "sunset red", "why sunsets are red", "sunsets red",
        "why is the sunset red", "red sunset", "orange sunset"],
       "Sunlight looks white but contains every colour, and each colour travels as a wave of a "
       "different length. Blue light has a short wavelength, so it bounces off the gas molecules "
       "in the air far more often than red light does. That bouncing is called Rayleigh "
       "scattering, and it is why the sky glows blue in every direction you look.",
       "Scattering strength rises sharply as wavelength falls - roughly with the fourth power of "
       "frequency - so blue light is scattered about five to ten times more than red. The "
       "scattered blue reaches your eye from all over the sky, not just from the direction of "
       "the sun, which is why the whole dome looks blue rather than a bright spot.",
       ["Look away from the sun, not at it: the sky is blue in every direction because the light "
        "has been scattered towards you.",
        "At sunset the light crosses much more air, so most of the blue is scattered away before "
        "it arrives and what is left looks orange or red.",
        "The violet in sunlight is scattered even more than blue, but our eyes are far less "
        "sensitive to violet and some of it is absorbed high in the atmosphere, so we see blue.",
        "On the Moon there is no air, so the sky is black even in daylight - the same reason a "
        "cloudless sky looks blue here."],
       "Shorter answer: air molecules scatter short wavelengths (blue) much more than long ones "
       "(red), and that scattered blue light reaches your eye from all parts of the sky."),
    _e("Why the ocean is salty",
       ["ocean salty", "sea salty", "why is the sea", "salt in the ocean", "ocean salt"],
       "The sea is salty because rain has been washing tiny amounts of salt out of rocks for "
       "billions of years, and that salt has nowhere to go once it reaches the ocean.",
       "Rain is fresh water, but as it runs over land it dissolves minerals from rock - sodium "
       "and chloride among them - and carries them down rivers to the sea. Water leaves the "
       "ocean again by evaporation, which takes only the water and leaves the salt behind. Over "
       "a very long time the salt accumulates to about 3.5 percent of the ocean's mass.",
       ["A closed lake in a dry place, such as the Dead Sea, shows the same effect faster: water "
        "evaporates, salt stays, concentration climbs.",
        "Some salt also arrives from underwater volcanic vents and hydrothermal springs.",
        "The overall saltiness has been roughly steady for a long time because salt is also "
        "removed - in sea spray, in deposits, and in the bodies of living things."],
       "Fresh water in, water vapour out, salt stays. Repeat for a few billion years."),

    # ------------------------------------------------------------ technology
    _e("Phone battery draining fast",
       ["phone battery", "battery drain", "drains fast", "battery dies", "battery life",
        "phone charge", "battery draining", "android battery", "iphone battery"],
       "A phone battery drains fast when the screen, the radios (Wi-Fi, mobile data, "
       "Bluetooth, GPS) or an app in the background keeps the processor awake.",
       "The single biggest cause is screen brightness and screen-on time, followed by weak "
       "mobile signal - the phone boosts its radio power to hold a connection - and apps "
       "that keep waking the CPU in the background.",
       ["Lower brightness and turn on adaptive brightness.",
        "Set the screen timeout shorter (30 seconds is plenty).",
        "Open Settings, Battery, and check which apps used the most power since the last charge.",
        "Restrict heavy background apps: long-press the app, App info, Battery, then 'Restricted'.",
        "Turn off Wi-Fi/Bluetooth/GPS when you are not using them, and switch off Wi-Fi scanning.",
        "Charge between 20% and 80% where you can; deep discharges every day age the cell faster.",
        "If the phone is two or more years old, the battery may simply be worn out - check the "
        "battery health screen or ask for a replacement."],
       "Battery settings differ slightly between Android and iPhone, but the order above works "
       "on both."),
    _e("Phone getting hot",
       ["phone hot", "phone heating", "phone gets warm", "overheating phone", "overheat"],
       "A phone gets warm when it is doing more work than the heat design can remove - heavy "
       "apps, charging, or direct sun.",
       "Charging while gaming or navigating is the most common combination: the battery and the "
       "processor both produce heat at the same time.",
       ["Stop charging while gaming or using the camera for long periods.",
        "Take the case off when it gets hot so heat can leave the body.",
        "Keep it out of direct sun and off car dashboards.",
        "Close apps you are not using; lower the refresh rate if the phone offers it.",
        "If it is hot while idle, check for a stuck background app or a bad update."]),
    _e("Slow phone or computer",
       ["phone slow", "computer slow", "laptop slow", "device slow", "sluggish"],
       "Most slow devices are limited by full storage, too many background apps, or an ageing "
       "battery that forces the processor to run slower.",
       "Storage below about 10% free leaves the system no room to cache, so everything reads "
       "from slow flash memory instead.",
       ["Free up storage until you have at least 15% free.",
        "Restart the device - it clears leaked memory and stuck background tasks.",
        "Uninstall or disable apps you have not opened in a month.",
        "Check for system updates, then for a failing battery if the device is old."]),
    _e("Wi-Fi connected but no internet",
       ["wifi no internet", "wifi connected no internet", "internet not working",
        "no internet connection", "wifi problem"],
       "'Connected, no internet' means the phone reached the router but the router could not "
       "reach the wider internet.",
       "Either the router's uplink is down, the router has stopped handing out addresses, or the "
       "phone saved a broken network configuration.",
       ["Restart the router (unplug 30 seconds) and the phone.",
        "On the phone, forget the Wi-Fi network and join it again.",
        "Test another device on the same Wi-Fi: if it also fails, the problem is the router or the ISP.",
        "Set DNS to 1.1.1.1 or 8.8.8.8 in the Wi-Fi settings if pages still time out.",
        "If only one app fails, check that app's permissions and any VPN."]),
    _e("Getting better at coding",
       ["get better at coding", "learn to code", "learn programming", "better programmer",
        "coding practice", "programming skill"],
       "You get better at coding by writing small programs that do something you actually want, "
       "then reading code you did not write.",
       "Progress comes from feedback loops: write, run, see the error, fix it. Tutorials alone "
       "give no error messages, so nothing sticks.",
       ["Pick one language and stay with it for three months (Python is a good default).",
        "Do 20-30 minutes of deliberate practice daily rather than five hours once a week.",
        "Build tiny tools: a to-do list, a file renamer, a small web page. Finish them.",
        "When something breaks, read the error message from the top line.",
        "Read one good open-source file a week and rewrite a small part of it.",
        "Use version control from day one so you can undo mistakes.",
        "Explain a concept out loud or in writing; gaps in the explanation are gaps in understanding."],
       "Consistency beats intensity. Ten focused minutes every day for a year beats a weekend "
       "crash course."),
    _e("Learning English faster",
       ["learn english", "improve english", "english speaking", "speak english better",
        "english practice"],
       "English improves fastest when you use it daily for real things - reading what you enjoy, "
       "writing short texts, and speaking out loud - instead of only studying rules.",
       "Grammar rules are useful for checking, but fluency comes from repeated exposure and "
       "output, so input and speaking must be daily.",
       ["Read something slightly above your level for 15 minutes a day.",
        "Keep a two-line daily journal in English and correct it the next day.",
        "Learn words in phrases ('make a decision'), not alone ('decision').",
        "Speak aloud for five minutes a day - describe your day or repeat a video's sentences.",
        "Watch with English subtitles first, then without.",
        "Pick five mistakes you make often, and fix only those for a week.",
        "Record yourself once a week and compare with last week."]),
    _e("Affect vs effect",
       ["affect vs effect", "affect or effect", "effect or affect"],
       "'Affect' is usually a verb meaning to influence something; 'effect' is usually a noun "
       "meaning a result.",
       "They sound alike but have different jobs in a sentence, so the test is what the word is "
       "doing: action or thing.",
       ["If you can replace it with 'influence', use affect (verb).",
        "If you can put 'the' before it and it names a result, use effect (noun).",
        "Exceptions: 'affect' is a noun in psychology (a flat emotional display) and 'effect' is "
        "a verb in 'effect a change' - rare in normal writing."],
       facts=["Example: 'Lack of sleep affects your memory.' (verb)",
              "Example: 'The effect of lack of sleep is poor memory.' (noun)"]),
    _e("Their, there and they're",
       ["their vs there", "there or their", "theirs", "there their theyre"],
       "'There' is about place, 'their' shows ownership, and \"they're\" means 'they are'.",
       "The apostrophe in \"they're\" marks a missing letter, exactly like 'do not' becomes "
       "'don't'.",
       ["Substitute 'they are' - if it fits, write they're.",
        "Substitute 'here' for place - if it fits, write there.",
        "Otherwise, if it shows who owns something, write their."]),
    _e("Your vs you're",
       ["your vs youre", "your or you're", "youre"],
       "'Your' shows ownership; \"you're\" means 'you are'.",
       "Same apostrophe rule as \"they're\": the mark replaces the missing 'a'.",
       ["Try 'you are' in the sentence. If it sounds right, write you're.",
        "If it sounds wrong, write your."]),
    _e("Its vs it's",
       ["its vs it's", "its or it's", "it's its"],
       "\"It's\" means 'it is' or 'it has'; 'its' shows ownership.",
       "Possessive pronouns never take an apostrophe - 'his', 'hers', 'theirs', 'its'.",
       ["Try 'it is'. If the sentence still works, write it's.",
        "Otherwise write its."]),

    # ---------------------------------------------------------------- health
    _e("Sleep better",
       ["sleep better", "cant sleep", "insomnia", "sleep problem", "fall asleep",
        "sleep quality", "tired all day"],
       "Sleep improves most reliably with a fixed wake-up time, morning daylight, and less "
       "screen light in the last hour before bed.",
       "Your body clock is set mainly by light and by when you get up, not by when you go to bed.",
       ["Wake up at the same time every day, including weekends.",
        "Get 10-20 minutes of daylight soon after waking.",
        "Stop caffeine after about 2 pm; it stays in the body for six hours or more.",
        "Dim screens an hour before bed and keep the room cool and dark.",
        "If you cannot sleep after 20 minutes, get up and do something dull in low light.",
        "Avoid alcohol as a sleep aid - it fragments the second half of the night."],
       "If poor sleep lasts more than a few weeks, or you snore heavily and wake unrefreshed, "
       "speak to a doctor."),
    _e("Headache relief",
       ["headache", "head pain", "migraine", "head hurts"],
       "Most headaches are tension-type: tight muscles around the neck and scalp, often with "
       "dehydration or screen strain.",
       "Long screen hours, skipped meals, low water intake and poor posture all feed into it.",
       ["Drink a glass of water first.",
        "Take a five-minute break from screens and look at something far away.",
        "Relax shoulders and jaw deliberately; loosen the neck.",
        "Eat something if you have skipped a meal.",
        "For regular pain, rest in a quiet dark room.",
        "See a doctor for sudden severe headache, headache with fever or weakness, or a new "
        "pattern after age 50."]),
    _e("Staying healthy with a desk job",
       ["desk job health", "sitting all day", "office health", "back pain sitting"],
       "The main risks of desk work are long unbroken sitting, screen strain and neck posture - "
       "and all three respond to small frequent changes.",
       "The body tolerates positions, not stillness: any position held for hours becomes a strain.",
       ["Stand or walk for two minutes every 30-40 minutes.",
        "Set the screen top at eye level and an arm's length away.",
        "Follow 20-20-20 for eyes: every 20 minutes look 20 feet away for 20 seconds.",
        "Keep elbows near 90 degrees and feet flat.",
        "Add two short walks to the day rather than one long workout.",
        "Strengthen back and core twice a week."]),

    # ----------------------------------------------------------------- money
    _e("Saving money on a small income",
       ["save money", "saving money", "budget", "spend less", "money management"],
       "Saving works when money leaves the account before you can spend it, not after.",
       "Willpower fails against convenience: automatic transfers and a separate account remove "
       "the daily decision.",
       ["Write down one month of spending - every item - to see where money actually goes.",
        "Pick the three biggest variable costs and cut one of them this month.",
        "Automate a transfer to savings on payday, even if it is small.",
        "Pay high-interest debt before low-interest savings.",
        "Use a 24-hour rule for any non-essential purchase over a set amount.",
        "Keep a small emergency buffer before investing in anything."]),
    _e("Building credit safely",
       ["build credit", "credit score", "credit history", "improve credit"],
       "Credit scores reward a long record of on-time payments and low balances relative to "
       "limits.",
       "Lenders are predicting repayment risk, so consistency over years matters more than any "
       "single month.",
       ["Pay at least the full statement balance by the due date, every month.",
        "Keep usage below about 30% of the limit, ideally under 10%.",
        "Do not open many new accounts at once.",
        "Keep old accounts open - length of history helps.",
        "Check your report for errors once a year and dispute them."]),

    # ---------------------------------------------------------------- study
    _e("Studying more effectively",
       ["study better", "study effectively", "memorise", "memorize", "exam preparation",
        "revise for exam", "learn faster"],
       "Active recall and spaced repetition beat re-reading and highlighting by a wide margin.",
       "Memory strengthens when you retrieve information with effort and revisit it just before "
       "you would forget it.",
       ["Close the book and write down everything you remember from the last section.",
        "Turn headings into questions and answer them without notes.",
        "Review after 1 day, 3 days, 1 week, then 1 month.",
        "Mix problem types in one session instead of doing 20 of the same kind.",
        "Explain the topic to an imaginary beginner; note where you stumble.",
        "Sleep after studying - consolidation happens during sleep."]),
    _e("Beating procrastination",
       ["procrastination", "stop procrastinating", "cant start studying", "focus better",
        "distraction"],
       "Procrastination is usually an emotional problem, not a time problem: the task feels "
       "unpleasant or unclear, so you avoid it.",
       "Making the first step absurdly small and removing friction both work better than trying "
       "to force motivation.",
       ["Shrink the first step to two minutes ('open the file and write one line').",
        "Decide the exact next action before you stop working.",
        "Put the phone in another room while working.",
        "Work in 25-minute blocks with a real break.",
        "Write down the distraction instead of following it."]),

    # --------------------------------------------------------------- cooking
    _e("Cooking chicken and rice",
       ["cook chicken and rice", "chicken rice recipe", "easy dinner chicken", "dinner ideas"],
       "The simplest reliable dinner is rice cooked in the same pot as seasoned chicken, or "
       "rice with chicken pan-fried separately and a quick sauce.",
       "Rice needs about 18 minutes at a gentle simmer; chicken breast needs to reach 74 °C "
       "internally, so timing both in one pot is easiest.",
       ["Rinse 1 cup of rice until the water runs clear.",
        "Soften onion in oil, add spices (cumin, turmeric, chilli, salt), then the chicken pieces.",
        "Brown the chicken for 5 minutes, then add 1.5 cups of water or stock.",
        "Add the rice, bring to a boil, cover and simmer on low for 18 minutes.",
        "Rest off the heat for 5 minutes, then fluff with a fork.",
        "Finish with lemon, coriander or fried onion."],
       "For a faster version, cook rice plain and pan-fry the chicken with garlic, soy sauce "
       "and honey."),
    _e("Cooking rice that is not sticky",
       ["rice sticky", "cook rice", "perfect rice", "rice mushy"],
       "Sticky or mushy rice comes from too much water, stirring, or lifting the lid while it "
       "steams.",
       "Rice absorbs a fixed amount of water; extra water turns to starch paste.",
       ["Use 1 part rice to 1.5 parts water for long-grain.",
        "Rinse the rice until the water is mostly clear.",
        "Bring to a boil, then cover and cook on the lowest heat for 18 minutes.",
        "Do not stir and do not lift the lid.",
        "Rest 5 minutes off the heat, then fluff."]),

    # -------------------------------------------------------------- practical
    _e("Removing a bad smell from a room",
       ["bad smell room", "room smells", "remove smell", "musty smell", "odour"],
       "Find the source first: damp fabric, a drain, a bin or a wet wall. Covering the smell "
       "with fragrance makes it worse.",
       "Most persistent smells are microbial - mould or bacteria in something damp.",
       ["Wash or air fabrics, including curtains and rugs.",
        "Clean the bin and the drain, then pour boiling water down the drain.",
        "Ventilate for 15 minutes a day, even in winter.",
        "Use a moisture absorber in small damp rooms.",
        "Fix leaks - a wet patch will keep smelling until it dries."]),
    _e("Getting rid of fruit flies",
       ["fruit flies", "gnats in kitchen", "flies in house"],
       "Fruit flies breed in over-ripe fruit, wet bins and drain sludge, so removing those "
       "sources ends the cycle.",
       "One pair can produce hundreds of eggs in a week, so cleaning is faster than catching.",
       ["Take out the bin daily while there is an infestation.",
        "Store fruit in the fridge or a covered bowl.",
        "Clean the drain with boiling water and a brush.",
        "Make a trap: a small bowl of vinegar with a drop of soap, covered with cling film "
        "with holes poked in it."]),
    _e("Interview preparation",
       ["interview tips", "job interview", "prepare for interview", "interview questions"],
       "Interview preparation is mostly about specific examples of things you actually did, "
       "told in a clear structure.",
       "Interviewers are checking whether you can do the job and how you behave when unsure; "
       "concrete stories answer both.",
       ["Write six stories: a success, a failure, a conflict, a deadline, a piece of learning, "
        "and a time you led something.",
        "For each, use situation, action, result - two minutes each.",
        "Research the company's product and one recent change.",
        "Prepare three questions to ask them.",
        "Practise out loud, once with a recording.",
        "Prepare a short, honest answer for 'what is your weakness?' plus what you are doing "
        "about it."]),
    _e("Writing a CV that gets replies",
       ["cv", "resume", "curriculum vitae", "cv help", "resume help"],
       "A CV gets replies when the top third matches the job advertisement word for word in "
       "skills and results.",
       "Recruiters scan for evidence of the exact tasks in the advert, so generic duties lose "
       "to measurable outcomes.",
       ["Keep it to one page unless you have 10+ years of experience.",
        "Put a two-line summary and your three strongest skills at the top.",
        "Write bullets as action + number: 'cut reporting time 40% by automating weekly exports'.",
        "Mirror the words the advert uses for skills you genuinely have.",
        "Remove photos, age, marital status and unrelated hobbies.",
        "Save as PDF and name the file with your own name."]),
    _e("Fixing a slow laptop",
       ["slow laptop", "laptop slow", "computer running slow", "speed up laptop"],
       "Slow laptops are usually full (nearly full storage), short of memory, or running too "
       "many start-up programs.",
       "When memory runs out, the machine swaps to disk, which is orders of magnitude slower.",
       ["Delete or move files until at least 15% of the drive is free.",
        "Disable unnecessary start-up apps.",
        "Uninstall toolbars and 'boosters' - they slow machines down.",
        "Check the disk health and run the built-in clean-up tool.",
        "If RAM is under 8 GB, adding memory is usually the cheapest real upgrade.",
        "Replace a mechanical drive with an SSD before buying a new laptop."]),

    # -------------------------------------------------------------- life/how-to
    _e("Waking up early",
       ["wake up early", "morning routine", "get up early", "alarm snooze"],
       "You wake up early by going to bed earlier and keeping one fixed wake-up time, not by "
       "setting a louder alarm.",
       "The body clock needs about a week to shift, and snoozing breaks the shift every morning.",
       ["Set the same wake-up time every day for two weeks.",
        "Move bedtime earlier by 20 minutes every three nights.",
        "Get daylight within an hour of waking.",
        "Put the alarm across the room and stop using snooze.",
        "Avoid bright screens in the last hour before bed."]),
    _e("Staying motivated",
       ["stay motivated", "motivation", "lose motivation", "keep going"],
       "Motivation follows action more often than it precedes it: small completed tasks create "
       "the momentum people call motivation.",
       "Dopamine from visible progress is what sustains effort, so progress must be visible and "
       "frequent.",
       ["Define a task so small it cannot fail today.",
        "Track the streak visibly - a calendar with a mark per day.",
        "Attach the habit to an existing one ('after brushing teeth, I write one line').",
        "Reduce the number of decisions: prepare things the night before.",
        "Share the goal with one person who will ask about it."]),
    _e("Making friends as an adult",
       ["make friends", "making friends", "lonely", "friend making adult"],
       "Adult friendships form from repeated, unplanned contact - the same class, gym, team or "
       "club every week.",
       "Proximity plus repetition is the mechanism; one-off meetings rarely turn into friendship.",
       ["Join something that meets weekly and keep going for a month.",
        "Say yes to the first three invitations even if you are tired.",
        "Move from group chat to one-to-one: invite one person for coffee.",
        "Remember details and ask about them next time.",
        "Be the one who suggests the next meeting."]),
    _e("Managing anger in the moment",
       ["anger control", "angry", "calm down", "temper", "frustration"],
       "Anger peaks within seconds and drops if you do not act on it during that peak.",
       "The body's arousal response outlasts the trigger, so a short delay is what changes the "
       "outcome.",
       ["Name it: 'I am angry right now' - labelling reduces intensity.",
        "Breathe out longer than you breathe in, ten times.",
        "Leave the room for two minutes if you can.",
        "Write the angry message but do not send it.",
        "Return to the conversation only after the physical surge has passed."]),
    _e("Talking to someone who is grieving",
       ["grief", "someone died", "condolence", "support grieving friend"],
       "The most helpful thing is to show up and let them talk, without trying to fix the loss.",
       "Grief is not a problem to solve; company and practical help reduce isolation, which is "
       "the main risk.",
       ["Say simply: 'I am so sorry. I am here.'",
        "Mention the person by name if they do; do not avoid the topic.",
        "Ask what they need rather than guessing, and offer specific help ('I'll bring dinner "
        "on Thursday').",
        "Keep checking in after the first month, when support usually disappears.",
        "Avoid 'at least' and 'everything happens for a reason'."]),

    # -------------------------------------------------------------- travel/money
    _e("Planning a cheap trip",
       ["cheap travel", "travel on budget", "plan a trip", "travel cheap"],
       "Cheap travel comes from flexible dates, booking flights early or very late, and staying "
       "slightly outside the centre.",
       "Prices are driven by demand and season far more than by distance.",
       ["Set a total budget and split it into transport, stay, food, activities.",
        "Use date-flexible search and shift by a day or two.",
        "Book accommodation with free cancellation early, then recheck the price.",
        "Stay near public transport rather than in the tourist centre.",
        "Eat where locals eat, one street away from the main square.",
        "Keep a copy of documents offline and a small cash reserve."]),
]


# ---------------------------------------------------------------------------
# matching
# ---------------------------------------------------------------------------

def _norm(text: str) -> str:
    return re.sub(r"[^a-z0-9 ]+", " ", (text or "").lower()).replace("  ", " ").strip()


def find(subject: str, question: str = "") -> Optional[Dict[str, Any]]:
    """Return the best everyday entry for a subject, or None."""
    hay = _norm(subject + " " + question)
    if not hay.strip():
        return None
    best, best_score = None, 0.0
    for entry in EVERYDAY:
        for key in entry["keys"]:
            k = _norm(key)
            if not k:
                continue
            if k in hay:
                score = 10.0 + len(k.split()) * 2
                # a key that covers most of the subject is a much stronger match
                if len(k.split()) >= 2:
                    score += 2
                if score > best_score:
                    best, best_score = entry, score
    return best if best_score >= 10 else None


def material(entry: Dict[str, Any]) -> List[str]:
    """Flatten an entry into sentences the answer kit can use."""
    out: List[str] = []
    if entry.get("what"):
        out.append(entry["what"])
    if entry.get("why"):
        out.append(entry["why"])
    out.extend(entry.get("facts") or [])
    out.extend(entry.get("fix") or [])
    if entry.get("note"):
        out.append(entry["note"])
    return out


def count() -> int:
    return len(EVERYDAY)
