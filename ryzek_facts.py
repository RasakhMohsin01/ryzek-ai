#!/usr/bin/env python3
"""
Ryzek AI - direct factual answers.

Problem this solves: a cached Wikipedia article about one capital used to win
BM25 for EVERY "capital of X" question, so "capital of France" returned a
paragraph about Kyoto. This module answers exact, checkable facts FIRST, then
adds depth-appropriate context. No retrieved passage can override the fact.

All data here is stable, widely documented, public knowledge. Where a fact is
genuinely contested, the wording says so instead of asserting a single answer.
"""

from __future__ import annotations

import difflib
import re
from typing import Dict, List, Optional, Tuple

# ---------------------------------------------------------------------------
# Country -> capital. Keys are lowercase aliases; values are (country, capital).
# ---------------------------------------------------------------------------

_COUNTRIES: List[Tuple[str, str, List[str]]] = [
    ("Afghanistan", "Kabul", ["afghanistan"]),
    ("Albania", "Tirana", ["albania"]),
    ("Algeria", "Algiers", ["algeria"]),
    ("Andorra", "Andorra la Vella", ["andorra"]),
    ("Angola", "Luanda", ["angola"]),
    ("Antigua and Barbuda", "Saint John's", ["antigua and barbuda", "antigua"]),
    ("Argentina", "Buenos Aires", ["argentina"]),
    ("Armenia", "Yerevan", ["armenia"]),
    ("Australia", "Canberra", ["australia"]),
    ("Austria", "Vienna", ["austria"]),
    ("Azerbaijan", "Baku", ["azerbaijan"]),
    ("Bahamas", "Nassau", ["bahamas", "the bahamas"]),
    ("Bahrain", "Manama", ["bahrain"]),
    ("Bangladesh", "Dhaka", ["bangladesh"]),
    ("Barbados", "Bridgetown", ["barbados"]),
    ("Belarus", "Minsk", ["belarus"]),
    ("Belgium", "Brussels", ["belgium"]),
    ("Belize", "Belmopan", ["belize"]),
    ("Benin", "Porto-Novo", ["benin"]),
    ("Bhutan", "Thimphu", ["bhutan"]),
    ("Bolivia", "Sucre", ["bolivia"]),
    ("Bosnia and Herzegovina", "Sarajevo", ["bosnia and herzegovina", "bosnia"]),
    ("Botswana", "Gaborone", ["botswana"]),
    ("Brazil", "Brasília", ["brazil", "brasil"]),
    ("Brunei", "Bandar Seri Begawan", ["brunei"]),
    ("Bulgaria", "Sofia", ["bulgaria"]),
    ("Burkina Faso", "Ouagadougou", ["burkina faso"]),
    ("Burundi", "Gitega", ["burundi"]),
    ("Cabo Verde", "Praia", ["cabo verde", "cape verde"]),
    ("Cambodia", "Phnom Penh", ["cambodia"]),
    ("Cameroon", "Yaoundé", ["cameroon"]),
    ("Canada", "Ottawa", ["canada"]),
    ("Central African Republic", "Bangui", ["central african republic"]),
    ("Chad", "N'Djamena", ["chad"]),
    ("Chile", "Santiago", ["chile"]),
    ("China", "Beijing", ["china", "people's republic of china", "prc"]),
    ("Colombia", "Bogotá", ["colombia"]),
    ("Comoros", "Moroni", ["comoros"]),
    ("Congo (Democratic Republic)", "Kinshasa", ["democratic republic of the congo", "dr congo", "drc", "congo kinshasa"]),
    ("Congo (Republic)", "Brazzaville", ["republic of the congo", "congo brazzaville"]),
    ("Costa Rica", "San José", ["costa rica"]),
    ("Croatia", "Zagreb", ["croatia"]),
    ("Cuba", "Havana", ["cuba"]),
    ("Cyprus", "Nicosia", ["cyprus"]),
    ("Czechia", "Prague", ["czechia", "czech republic"]),
    ("Denmark", "Copenhagen", ["denmark"]),
    ("Djibouti", "Djibouti", ["djibouti"]),
    ("Dominica", "Roseau", ["dominica"]),
    ("Dominican Republic", "Santo Domingo", ["dominican republic"]),
    ("Ecuador", "Quito", ["ecuador"]),
    ("Egypt", "Cairo", ["egypt"]),
    ("El Salvador", "San Salvador", ["el salvador"]),
    ("Equatorial Guinea", "Malabo", ["equatorial guinea"]),
    ("Eritrea", "Asmara", ["eritrea"]),
    ("Estonia", "Tallinn", ["estonia"]),
    ("Eswatini", "Mbabane", ["eswatini", "swaziland"]),
    ("Ethiopia", "Addis Ababa", ["ethiopia"]),
    ("Fiji", "Suva", ["fiji"]),
    ("Finland", "Helsinki", ["finland"]),
    ("France", "Paris", ["france"]),
    ("Gabon", "Libreville", ["gabon"]),
    ("Gambia", "Banjul", ["gambia", "the gambia"]),
    ("Georgia", "Tbilisi", ["georgia the country", "georgia country"]),
    ("Germany", "Berlin", ["germany"]),
    ("Ghana", "Accra", ["ghana"]),
    ("Greece", "Athens", ["greece"]),
    ("Grenada", "St. George's", ["grenada"]),
    ("Guatemala", "Guatemala City", ["guatemala"]),
    ("Guinea", "Conakry", ["guinea"]),
    ("Guinea-Bissau", "Bissau", ["guinea-bissau", "guinea bissau"]),
    ("Guyana", "Georgetown", ["guyana"]),
    ("Haiti", "Port-au-Prince", ["haiti"]),
    ("Honduras", "Tegucigalpa", ["honduras"]),
    ("Hungary", "Budapest", ["hungary"]),
    ("Iceland", "Reykjavík", ["iceland"]),
    ("India", "New Delhi", ["india"]),
    ("Indonesia", "Jakarta", ["indonesia"]),
    ("Iran", "Tehran", ["iran", "persia"]),
    ("Iraq", "Baghdad", ["iraq"]),
    ("Ireland", "Dublin", ["ireland", "republic of ireland"]),
    ("Israel", "Jerusalem", ["israel"]),
    ("Italy", "Rome", ["italy"]),
    ("Ivory Coast", "Yamoussoukro", ["ivory coast", "côte d'ivoire", "cote d'ivoire"]),
    ("Jamaica", "Kingston", ["jamaica"]),
    ("Japan", "Tokyo", ["japan"]),
    ("Jordan", "Amman", ["jordan"]),
    ("Kazakhstan", "Astana", ["kazakhstan"]),
    ("Kenya", "Nairobi", ["kenya"]),
    ("Kiribati", "South Tarawa", ["kiribati"]),
    ("Kuwait", "Kuwait City", ["kuwait"]),
    ("Kyrgyzstan", "Bishkek", ["kyrgyzstan"]),
    ("Laos", "Vientiane", ["laos"]),
    ("Latvia", "Riga", ["latvia"]),
    ("Lebanon", "Beirut", ["lebanon"]),
    ("Lesotho", "Maseru", ["lesotho"]),
    ("Liberia", "Monrovia", ["liberia"]),
    ("Libya", "Tripoli", ["libya"]),
    ("Liechtenstein", "Vaduz", ["liechtenstein"]),
    ("Lithuania", "Vilnius", ["lithuania"]),
    ("Luxembourg", "Luxembourg", ["luxembourg"]),
    ("Madagascar", "Antananarivo", ["madagascar"]),
    ("Malawi", "Lilongwe", ["malawi"]),
    ("Malaysia", "Kuala Lumpur", ["malaysia"]),
    ("Maldives", "Malé", ["maldives"]),
    ("Mali", "Bamako", ["mali"]),
    ("Malta", "Valletta", ["malta"]),
    ("Marshall Islands", "Majuro", ["marshall islands"]),
    ("Mauritania", "Nouakchott", ["mauritania"]),
    ("Mauritius", "Port Louis", ["mauritius"]),
    ("Mexico", "Mexico City", ["mexico"]),
    ("Micronesia", "Palikir", ["micronesia", "federated states of micronesia"]),
    ("Moldova", "Chișinău", ["moldova"]),
    ("Monaco", "Monaco", ["monaco"]),
    ("Mongolia", "Ulaanbaatar", ["mongolia"]),
    ("Montenegro", "Podgorica", ["montenegro"]),
    ("Morocco", "Rabat", ["morocco"]),
    ("Mozambique", "Maputo", ["mozambique"]),
    ("Myanmar", "Naypyidaw", ["myanmar", "burma"]),
    ("Namibia", "Windhoek", ["namibia"]),
    ("Nauru", "Yaren", ["nauru"]),
    ("Nepal", "Kathmandu", ["nepal"]),
    ("Netherlands", "Amsterdam", ["netherlands", "holland", "the netherlands"]),
    ("New Zealand", "Wellington", ["new zealand"]),
    ("Nicaragua", "Managua", ["nicaragua"]),
    ("Niger", "Niamey", ["niger"]),
    ("Nigeria", "Abuja", ["nigeria"]),
    ("North Korea", "Pyongyang", ["north korea", "dprk"]),
    ("North Macedonia", "Skopje", ["north macedonia", "macedonia"]),
    ("Norway", "Oslo", ["norway"]),
    ("Oman", "Muscat", ["oman"]),
    ("Pakistan", "Islamabad", ["pakistan"]),
    ("Palau", "Ngerulmud", ["palau"]),
    ("Panama", "Panama City", ["panama"]),
    ("Papua New Guinea", "Port Moresby", ["papua new guinea"]),
    ("Paraguay", "Asunción", ["paraguay"]),
    ("Peru", "Lima", ["peru"]),
    ("Philippines", "Manila", ["philippines", "the philippines"]),
    ("Poland", "Warsaw", ["poland"]),
    ("Portugal", "Lisbon", ["portugal"]),
    ("Qatar", "Doha", ["qatar"]),
    ("Romania", "Bucharest", ["romania"]),
    ("Russia", "Moscow", ["russia", "russian federation"]),
    ("Rwanda", "Kigali", ["rwanda"]),
    ("Saint Kitts and Nevis", "Basseterre", ["saint kitts and nevis"]),
    ("Saint Lucia", "Castries", ["saint lucia"]),
    ("Saint Vincent and the Grenadines", "Kingstown", ["saint vincent and the grenadines"]),
    ("Samoa", "Apia", ["samoa"]),
    ("San Marino", "San Marino", ["san marino"]),
    ("Sao Tome and Principe", "São Tomé", ["sao tome and principe", "são tomé and príncipe"]),
    ("Saudi Arabia", "Riyadh", ["saudi arabia"]),
    ("Senegal", "Dakar", ["senegal"]),
    ("Serbia", "Belgrade", ["serbia"]),
    ("Seychelles", "Victoria", ["seychelles"]),
    ("Sierra Leone", "Freetown", ["sierra leone"]),
    ("Singapore", "Singapore", ["singapore"]),
    ("Slovakia", "Bratislava", ["slovakia"]),
    ("Slovenia", "Ljubljana", ["slovenia"]),
    ("Solomon Islands", "Honiara", ["solomon islands"]),
    ("Somalia", "Mogadishu", ["somalia"]),
    ("South Africa", "Pretoria, Cape Town and Bloemfontein", ["south africa"]),
    ("South Korea", "Seoul", ["south korea", "republic of korea"]),
    ("South Sudan", "Juba", ["south sudan"]),
    ("Spain", "Madrid", ["spain"]),
    ("Sri Lanka", "Sri Jayawardenepura Kotte", ["sri lanka"]),
    ("Sudan", "Khartoum", ["sudan"]),
    ("Suriname", "Paramaribo", ["suriname"]),
    ("Sweden", "Stockholm", ["sweden"]),
    ("Switzerland", "Bern", ["switzerland"]),
    ("Syria", "Damascus", ["syria"]),
    ("Taiwan", "Taipei", ["taiwan"]),
    ("Tajikistan", "Dushanbe", ["tajikistan"]),
    ("Tanzania", "Dodoma", ["tanzania"]),
    ("Thailand", "Bangkok", ["thailand"]),
    ("Timor-Leste", "Dili", ["timor-leste", "east timor"]),
    ("Togo", "Lomé", ["togo"]),
    ("Tonga", "Nukuʻalofa", ["tonga"]),
    ("Trinidad and Tobago", "Port of Spain", ["trinidad and tobago"]),
    ("Tunisia", "Tunis", ["tunisia"]),
    ("Turkey", "Ankara", ["turkey", "türkiye"]),
    ("Turkmenistan", "Ashgabat", ["turkmenistan"]),
    ("Tuvalu", "Funafuti", ["tuvalu"]),
    ("Uganda", "Kampala", ["uganda"]),
    ("Ukraine", "Kyiv", ["ukraine", "kiev"]),
    ("United Arab Emirates", "Abu Dhabi", ["united arab emirates", "uae"]),
    ("United Kingdom", "London", ["united kingdom", "uk", "britain", "great britain", "england"]),
    ("United States", "Washington, D.C.", ["united states", "usa", "us", "america", "united states of america"]),
    ("Uruguay", "Montevideo", ["uruguay"]),
    ("Uzbekistan", "Tashkent", ["uzbekistan"]),
    ("Vanuatu", "Port Vila", ["vanuatu"]),
    ("Vatican City", "Vatican City", ["vatican city", "vatican", "holy see"]),
    ("Venezuela", "Caracas", ["venezuela"]),
    ("Vietnam", "Hanoi", ["vietnam"]),
    ("Yemen", "Sanaa", ["yemen"]),
    ("Zambia", "Lusaka", ["zambia"]),
    ("Zimbabwe", "Harare", ["zimbabwe"]),
]

CAPITALS: Dict[str, Tuple[str, str]] = {}
CAPITAL_TO_COUNTRY: Dict[str, str] = {}
for _country, _capital, _aliases in _COUNTRIES:
    for _alias in _aliases + [_country.lower()]:
        CAPITALS[_alias] = (_country, _capital)
    CAPITAL_TO_COUNTRY[_capital.lower()] = _country
    # also index the first city for multi-capital countries
    if ", " in _capital:
        CAPITAL_TO_COUNTRY[_capital.split(",")[0].strip().lower()] = _country

# Extra well-known aliases that are not country names.
CAPITALS["the us"] = CAPITALS["united states"]
CAPITALS["the uk"] = CAPITALS["united kingdom"]
CAPITALS["u.s."] = CAPITALS["united states"]
CAPITALS["u.k."] = CAPITALS["united kingdom"]

# Carefully worded notes for the capitals people most often confuse.
NOTES: Dict[str, str] = {
    "Australia": "Sydney and Melbourne are larger and better known, but Canberra was chosen as a purpose-built compromise between the two.",
    "Brazil": "Rio de Janeiro was the capital until 1960, when the planned city of Brasília took over. São Paulo is the largest city, not the capital.",
    "Canada": "Toronto is the largest city, but Ottawa is the national capital.",
    "China": "Shanghai is the largest city; Beijing is the capital.",
    "India": "New Delhi is the capital, a planned district within the larger city of Delhi. Mumbai is the financial centre, not the capital.",
    "Japan": "Tokyo is the seat of government and is widely accepted as the capital. Kyoto was the imperial capital from 794 until 1868, which is why older sources can be confusing.",
    "Nigeria": "Lagos was the capital until 1991; Abuja is the capital today.",
    "Pakistan": "Karachi was the first capital and is the largest city; Islamabad has been the capital since 1967.",
    "South Africa": "South Africa has three capitals: Pretoria (executive), Cape Town (legislative) and Bloemfontein (judicial). Johannesburg is the largest city but is not a capital.",
    "Switzerland": "Bern is the federal city; Zurich and Geneva are larger and host many international organisations, which causes frequent confusion.",
    "Turkey": "Istanbul was the Ottoman capital and is the largest city, but Ankara has been the capital of the republic since 1923.",
    "United States": "New York City was the first capital under the Constitution and is the largest city, but Washington, D.C. has been the capital since 1800.",
    "United Kingdom": "London is the capital of both the United Kingdom and England. Scotland, Wales and Northern Ireland have their own devolved capitals: Edinburgh, Cardiff and Belfast.",
    "Kazakhstan": "Astana was renamed Nur-Sultan in 2019 and reverted to Astana in 2022, so older references may use either name.",
    "Myanmar": "Yangon was the capital until 2005, when the government moved to the planned city of Naypyidaw.",
    "Sri Lanka": "Sri Jayawardenepura Kotte is the official legislative capital; Colombo is the largest city and the commercial capital.",
    "Tanzania": "Dar es Salaam remains the largest city and a major port; Dodoma is the official capital.",
    "Ivory Coast": "Yamoussoukro is the official capital, while Abidjan is the largest city and the economic centre.",
    "Bolivia": "Sucre is the constitutional capital; La Paz is the seat of government and the administrative centre.",
    "Benin": "Porto-Novo is the official capital; Cotonou is the largest city and the seat of government.",
    "Netherlands": "Amsterdam is the constitutional capital, while The Hague is the seat of government and the judiciary.",
    "Israel": "Israel designates Jerusalem as its capital; the status of Jerusalem is disputed internationally, so a neutral account states the claim rather than settling it.",
    "Ukraine": "Kyiv is the standard English spelling today; 'Kiev' reflects the older Russian-derived transliteration.",
}

GENERIC_NOTE = (
    "A capital is the city where a country's central government is seated. It is not always the "
    "largest or best-known city: Australia, Canada, Turkey, Brazil and Nigeria are all examples "
    "where the two differ. Capital status can also change, so a historical source may name an "
    "older capital."
)

# ---------------------------------------------------------------------------
# Other stable, checkable facts (with disputed cases flagged honestly)
# ---------------------------------------------------------------------------

QUICK_FACTS: List[Tuple[str, str, str]] = [
    (r"\b(how many continents|number of continents)\b",
     "Seven",
     "The seven-continent model used in most English-language education lists Africa, Antarctica, Asia, Europe, North America, Oceania (or Australia) and South America. Other models exist: some combine Europe and Asia into Eurasia, and some count the Americas as one continent, so the number depends on the convention being used."),
    (r"\b(largest planet|biggest planet)\b",
     "Jupiter",
     "Jupiter is the largest planet in the Solar System, with a mass more than twice that of all the other planets combined. It is a gas giant, so 'largest' can refer to diameter, volume or mass; Jupiter leads on all three."),
    (r"\b(largest ocean|biggest ocean)\b",
     "The Pacific Ocean",
     "The Pacific is the largest and deepest ocean on Earth, covering roughly a third of the planet's surface. It is larger than all of Earth's land area put together."),
    (r"\b(how many planets|number of planets)\b",
     "Eight",
     "The Solar System has eight recognised planets: Mercury, Venus, Earth, Mars, Jupiter, Saturn, Uranus and Neptune. Pluto was reclassified as a dwarf planet in 2006, which is why older books sometimes say nine."),
    (r"\b(speed of light|how fast does light travel)\b",
     "299,792,458 metres per second",
     "In a vacuum, light travels at exactly 299,792,458 m/s, about 300,000 km/s. The metre is defined from this constant and the definition of the second, so the value is exact by definition rather than a measurement with uncertainty."),
    (r"\b(boiling point of water|water boil)\b",
     "100 °C (212 °F) at standard atmospheric pressure",
     "Water boils at 100 °C at sea-level pressure. The boiling point falls as pressure falls, so water boils below 100 °C on a mountain and above 100 °C in a pressure cooker."),
    (r"\b(freezing point of water|water freeze)\b",
     "0 °C (32 °F) at standard atmospheric pressure",
     "Pure water freezes at 0 °C at sea-level pressure. Dissolved substances such as salt lower the freezing point, which is why roads are salted in winter."),
    (r"\b(how many bones|number of bones)\b",
     "206 in a typical adult",
     "A typical adult skeleton has 206 bones. Babies are born with around 270 separate bones, many of which fuse together during growth, which is why the two numbers differ."),
    (r"\b(chemical formula of water|formula for water|what is h2o)\b",
     "H₂O",
     "A water molecule contains two hydrogen atoms and one oxygen atom. The bent shape of the molecule and the polarity of its bonds explain many of water's unusual properties, including its high boiling point and its ability to dissolve salts."),
    (r"\b(how many days in a year|days in a year)\b",
     "365, or 366 in a leap year",
     "A calendar year has 365 days, with an extra day added in most years divisible by four. Century years are leap years only if divisible by 400, which is why 2000 was a leap year but 1900 was not."),
    (r"\b(first president of (?:the )?(?:united states|usa|us)|who was george washington)\b",
     "George Washington",
     "George Washington served as the first President of the United States from 1789 to 1797. He had previously commanded the Continental Army and presided over the Constitutional Convention."),
    (r"\b(largest country (?:in the world )?by area|biggest country by area)\b",
     "Russia",
     "Russia is the largest country by land area, spanning eastern Europe and northern Asia across eleven time zones. Rankings by population or by GDP give a completely different answer."),
    (r"\b(smallest country|smallest country in the world)\b",
     "Vatican City",
     "Vatican City is the smallest sovereign state by both area and population. 'Smallest' depends on recognising sovereignty, so some lists of dependent territories differ."),
    (r"\b(what is pi\b|value of pi\b)\b",
     "Approximately 3.14159",
     "Pi is the ratio of a circle's circumference to its diameter. It is irrational, so its decimal expansion never ends or repeats; 3.14159 is a rounded working value, not the whole number."),
    (r"\b(who wrote (?:hamlet|romeo and juliet|macbeth))\b",
     "William Shakespeare",
     "William Shakespeare wrote these plays in the late sixteenth and early seventeenth centuries. Authorship questions are sometimes raised about individual works, but the standard scholarly attribution is Shakespeare."),
]


# ---------------------------------------------------------------------------
# Detection
# ---------------------------------------------------------------------------

_CAPITAL_WORD = r"capit(?:al|el|il|le|ol)\b|cap\b"
_CAPITAL_REQUEST = re.compile(
    r"(?:" + _CAPITAL_WORD + r")", re.IGNORECASE
)


def _normalise(phrase: str) -> str:
    s = (phrase or "").lower().strip()
    s = re.sub(r"[^\w\s'’.\-]", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    s = re.sub(r"^(?:the|a|an)\s+", "", s)
    s = re.sub(r"\b(?:please|tell me|what is|whats|what's|which is|name|of|for|city|country)\b", " ", s)
    s = re.sub(r"\s+", " ", s).strip(" .?!,-'’")
    return s


def find_country(text: str) -> Optional[Tuple[str, str]]:
    """Return (country, capital) for a capital question, with fuzzy fallback."""
    low = " " + (text or "").lower().strip() + " "
    if not _CAPITAL_REQUEST.search(low):
        return None

    # reverse: "Tokyo is the capital of which country?"
    rev = re.search(r"\b([A-Za-z .'-]{2,40}?)\s+is\s+the\s+capit\w*\s+of\s+(?:which|what)\s+country", low, re.I)
    if rev:
        city = _normalise(rev.group(1))
        hit = CAPITAL_TO_COUNTRY.get(city)
        if hit:
            return hit, CAPITALS[hit.lower()][1]

    # standard: "capital of X", "X's capital", "capital of the X"
    candidates: List[str] = []
    for pattern in (
        r"capit\w*\s+(?:city\s+)?(?:of|for|in)\s+(?:the\s+)?(.+?)(?:\?|\.|!|$)",
        r"(?:what|which|tell me|name|give me).*?capit\w*\s+(?:of|for)\s+(?:the\s+)?(.+?)(?:\?|\.|!|$)",
        r"([A-Za-z .'-]{2,40}?)'s\s+capit\w*",
        r"capit\w*\s+of\s+([A-Za-z .'-]{2,40})",
    ):
        m = re.search(pattern, low, re.I)
        if m:
            candidates.append(m.group(1))
    # last fallback: everything after the word "capital"
    tail = re.split(r"\bcapit\w*\b", low, maxsplit=1)
    if len(tail) == 2:
        candidates.append(tail[1])

    for raw in candidates:
        name = _normalise(raw)
        if not name or len(name) > 45:
            continue
        if name in CAPITALS:
            return CAPITALS[name]
        # A phrase may contain extra words: take the longest alias that appears.
        matches = [a for a in CAPITALS if len(a) >= 4 and re.search(r"\b" + re.escape(a) + r"\b", name)]
        if matches:
            best = max(matches, key=len)
            return CAPITALS[best]
        close = difflib.get_close_matches(name, list(CAPITALS), n=1, cutoff=0.72)
        if close:
            return CAPITALS[close[0]]
    return None


def capital_answer(text: str, depth: str = "deep") -> Optional[str]:
    """Answer a capital question directly and correctly. None if not one."""
    if not _CAPITAL_REQUEST.search(text or ""):
        return None

    # "Tokyo is the capital of which country?" - answer the COUNTRY, not the city.
    rev = re.search(r"\b([A-Za-z .'-]{2,40}?)\s+is\s+the\s+capit\w*\s+of\s+"
                    r"(?:which|what)\s+country", text or "", re.I)
    if rev:
        city = _normalise(rev.group(1))
        hit = CAPITAL_TO_COUNTRY.get(city)
        if hit:
            cap = CAPITALS[hit.lower()][1]
            out = ["## Short answer", "",
                   f"**{hit}** - {city.title()} is its capital. That is the direct answer to "
                   "your question."]
            if depth != "quick":
                out += ["", "## In detail", "",
                        f"You named a city and asked for its country. {city.title()} is the "
                        f"capital of {hit}; {NOTES.get(hit, GENERIC_NOTE)}"]
            if depth in ("deep", "exhaustive"):
                out += ["", "## How to check it yourself", "",
                        "1. Look up the city in a current reference work.\n"
                        "2. Confirm the country it belongs to and whether it is the official capital.\n"
                        "3. Watch for cities that were capitals only historically.", "",
                        "## Sources", "",
                        "- Curated country-to-capital reference table in `ryzek_facts.py`.", "",
                        "## What I could not verify", "",
                        "Disputed territories and recent capital relocations need a current primary "
                        "source; I do not track those in real time."]
            out += ["", "## Keep going", "",
                    f"Ask me about {hit}'s geography or history, or name another capital city."]
            return "\n".join(out)

    found = find_country(text)
    if not found:
        return (
            "## Which capital?\n\nYou asked about a capital but didn't name a country, so I can't give "
            "a single city without guessing.\n\n## What I can tell you now\n\n" + GENERIC_NOTE +
            "\n\n## A few worked examples\n\n"
            "- Japan → Tokyo · France → Paris · Pakistan → Islamabad · Germany → Berlin\n"
            "- Australia → Canberra (not Sydney) · Canada → Ottawa (not Toronto)\n"
            "- Turkey → Ankara (not Istanbul) · Brazil → Brasília (not Rio de Janeiro)\n\n"
            "## Keep going\n\nAdd the country name - for example 'what is the capital of Japan?' - and I'll "
            "answer directly, then explain the context and the common mix-up."
        )
    country, capital = found
    is_multi = ", " in capital and " and " in capital
    verb = "are" if is_multi else "is"
    direct = f"The capital of {country} {verb} **{capital}**."
    if is_multi:
        direct = f"{country} has three capitals: **{capital}**."

    parts = ["## Short answer", "", direct + " " +
             "That is the direct answer to your question - no detour into a different country."]

    if depth != "quick":
        parts += ["", "## In detail", "",
                  NOTES.get(country, GENERIC_NOTE), "",
                  "A capital city is defined by where a country's government sits, not by size, "
                  "fame or economic weight. That distinction is the reason these questions so often "
                  "trip up a search engine: an article about one capital can mention several others, "
                  "and a ranking algorithm can pick the wrong paragraph. I answer from a curated "
                  "country-to-capital table, so the direct answer never drifts."]
    if depth in ("deep", "exhaustive"):
        parts += ["", "## How to check it yourself", "",
                  "1. Look up the country in a current reference work or its government's own site.\n"
                  "2. Check whether the source distinguishes the official capital from the largest city "
                  "or the seat of government.\n"
                  "3. Note the date of the source: capitals do change, and older material can name "
                  "the previous one.\n"
                  "4. For disputed cases, read how the source frames the claim rather than treating "
                  "one wording as final.", "",
                  "## Common mistakes and limits", "",
                  "- Assuming the biggest city is the capital.\n"
                  "- Confusing a historic capital with the current one.\n"
                  "- Treating a country with several capitals as if it had one.\n"
                  "- Trusting a search snippet that happens to mention your country inside an article "
                  "about a different one.", "",
                  "## Sources", "",
                  "- Curated country-to-capital reference table in `ryzek_facts.py` "
                  f"(currently covering {len(_COUNTRIES)} countries and territories).", "",
                  "## What I could not verify", "",
                  "I do not track recent capital relocations or contested status changes in real time. "
                  "If you need a legally precise answer for a disputed territory, check a current "
                  "primary source and tell me which convention you want me to use."]
    parts += ["", "## Keep going", "",
              "Ask me about the country's geography, history or languages, or name another country "
              "and I'll give you its capital directly. Type `/about` to see who built me."]
    return "\n".join(parts)


def quick_fact_answer(text: str, depth: str = "deep") -> Optional[str]:
    """Answer a small set of stable, checkable factual questions directly."""
    low = (text or "").lower()
    for pattern, answer, detail in QUICK_FACTS:
        if not re.search(pattern, low, re.I):
            continue
        parts = ["## Short answer", "", f"**{answer}**. " +
                 "That is the direct answer to your question."]
        if depth != "quick":
            parts += ["", "## In detail", "", detail]
        if depth in ("deep", "exhaustive"):
            parts += ["", "## Why the wording matters", "",
                      "Short factual questions usually hide an assumption about definitions. "
                      "Stating the convention first - what counts as a continent, a planet, a "
                      "capital, or a year - is what makes the answer accurate rather than merely "
                      "memorable.", "",
                      "## Common mistakes and limits", "",
                      "- Reciting a number without the convention behind it.\n"
                      "- Using an outdated classification (nine planets, older country names).\n"
                      "- Confusing an exact constant with a rounded working value.", "",
                      "## Sources", "",
                      "- Curated stable-fact reference in `ryzek_facts.py`.", "",
                      "## What I could not verify", "",
                      "If your question depends on a live measurement, a recent change or a "
                      "disputed classification, check a current primary source; I mark that "
                      "explicitly instead of inventing precision."]
        parts += ["", "## Keep going", "",
                  "Ask a follow-up about why that answer holds, or request a comparison with a "
                  "related quantity."]
        return "\n".join(parts)
    return None
