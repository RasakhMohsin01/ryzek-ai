#!/usr/bin/env python3
"""
Ryzek AI - live web research layer (v2.5).

The app no longer answers only from its local knowledge base. For a real
question it queries several independent online platforms in parallel, reads
the best pages it finds, and passes the material to the answer composer and
to the writing desk. Every result keeps its URL so the answer can cite it.

Sources: Google News (Google), Google Books (Google), Google web search,
Wikipedia, Simple Wikipedia, Bing, DuckDuckGo, Wikidata, Stack Overflow,
Open Library, GitHub and a generic web-page reader.

Standard library only. All network work is bounded by short timeouts, runs in
a thread pool, is cached on disk for 30 minutes, and never blocks a reply if
a platform refuses the request. A failed platform is reported honestly in the
status list instead of being silently replaced with invented facts.
"""

from __future__ import annotations

import base64
import hashlib
import html
import json
import os
import re
import threading
import time
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple
from urllib import request as urlrequest
from urllib.parse import parse_qs, quote, urlparse, urlunparse

ROOT = Path(__file__).resolve().parent
# Same data folder rule as ryzek_core: writable storage on Android.
CACHE_DIR = Path(os.environ.get("RYZEK_DATA") or (ROOT / "data")) / "web_cache"
CACHE_DIR.mkdir(parents=True, exist_ok=True)
CACHE_TTL = 1800  # 30 minutes

UA = ("Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36")
HEADERS = {"User-Agent": UA, "Accept-Language": "en-US,en;q=0.9",
           "Accept": "text/html,application/xhtml+xml,application/json;q=0.9,*/*;q=0.8"}

# Shown in the GUI's "Live sources" panel and in /api/web.
PLATFORMS: List[Dict[str, str]] = [
    {"id": "google", "label": "Google", "icon": "G", "color": "#4285f4",
     "desc": "Google News, Google Books and Google web results"},
    {"id": "wikipedia", "label": "Wikipedia", "icon": "W", "color": "#a6a6a6",
     "desc": "Encyclopedia articles and summaries"},
    {"id": "simplewiki", "label": "Simple Wikipedia", "icon": "S", "color": "#4f8ef7",
     "desc": "Plain-English definitions used to keep answers intermediate"},
    {"id": "bing", "label": "Bing", "icon": "b", "color": "#00b4d8",
     "desc": "Web results and snippets"},
    {"id": "duckduckgo", "label": "DuckDuckGo", "icon": "D", "color": "#de5833",
     "desc": "Independent web results and snippets"},
    {"id": "wikidata", "label": "Wikidata", "icon": "Q", "color": "#339966",
     "desc": "Structured facts and descriptions"},
    {"id": "stackoverflow", "label": "Stack Overflow", "icon": "SO", "color": "#f48024",
     "desc": "Programming questions and answers"},
    {"id": "openlibrary", "label": "Open Library", "icon": "OL", "color": "#6b8e23",
     "desc": "Books and reference descriptions"},
    {"id": "github", "label": "GitHub", "icon": "GH", "color": "#8b949e",
     "desc": "Open-source code and documentation"},
    {"id": "arxiv", "label": "arXiv", "icon": "aX", "color": "#b31b1b",
     "desc": "Physics, maths and computer-science preprints"},
    {"id": "crossref", "label": "Crossref", "icon": "DOI", "color": "#4a90d9",
     "desc": "Published papers with traceable DOIs"},
    {"id": "openalex", "label": "OpenAlex", "icon": "OA", "color": "#2f7d5d",
     "desc": "Open index of scholarly works"},
    {"id": "hackernews", "label": "Hacker News", "icon": "HN", "color": "#ff6600",
     "desc": "Practitioner discussion and releases"},
    {"id": "reddit", "label": "Reddit", "icon": "r/", "color": "#ff4500",
     "desc": "Real-world experience, marked as opinion"},
    {"id": "deepseek", "label": "DeepSeek", "icon": "DS", "color": "#4d6bfe",
     "desc": "Second reasoning pass (optional key)"},
    {"id": "grok", "label": "Grok", "icon": "x", "color": "#c9c9c9",
     "desc": "Second reasoning pass (optional key)"},
    {"id": "webpages", "label": "Web pages", "icon": "↗", "color": "#a78bfa",
     "desc": "Full text read directly from the best result pages"},
]

_STATUS_LOCK = threading.Lock()
LAST_STATUS: List[Dict[str, Any]] = []
LAST_QUERY = ""
LAST_TIME = 0.0


# ---------------------------------------------------------------------------
# Fetch + text helpers
# ---------------------------------------------------------------------------

def fetch(url: str, timeout: float = 6.0, extra: Optional[Dict[str, str]] = None) -> str:
    h = dict(HEADERS)
    if extra:
        h.update(extra)
    req = urlrequest.Request(url, headers=h)
    with urlrequest.urlopen(req, timeout=timeout) as resp:
        raw = resp.read(420_000)
        charset = resp.headers.get_content_charset() or "utf-8"
    return raw.decode(charset, "ignore")


def fetch_json(url: str, timeout: float = 6.0) -> Any:
    return json.loads(fetch(url, timeout, {"Accept": "application/json"}))


def strip_tags(fragment: str) -> str:
    fragment = re.sub(r"<(script|style|noscript|svg)\b.*?</\1>", " ", fragment, flags=re.S | re.I)
    fragment = re.sub(r"<br\s*/?>|</p>|</div>|</li>|</h\d>", " ", fragment, flags=re.I)
    fragment = re.sub(r"<[^>]+>", " ", fragment)
    return clean(html.unescape(fragment))


def clean(text: str, limit: int = 420) -> str:
    text = re.sub(r"\s+", " ", (text or "").replace("\xa0", " ")).strip()
    return text[:limit].rstrip() + ("…" if len(text) > limit else "")


def domain(url: str) -> str:
    try:
        return (urlparse(url).netloc or "").lower().replace("www.", "")
    except Exception:
        return ""


def item(title: str, url: str, snippet: str, source: str,
         text: str = "", kind: str = "web") -> Dict[str, str]:
    return {"title": clean(title, 150), "url": url, "snippet": clean(snippet, 420),
            "source": source, "domain": domain(url), "text": clean(text or snippet, 2400),
            "kind": kind}


def tidy_url(href: str) -> str:
    href = html.unescape(href or "")
    if href.startswith("//"):
        href = "https:" + href
    # DuckDuckGo wraps outbound links in /l/?uddg=...
    if "duckduckgo.com/l/" in href:
        try:
            qs = parse_qs(urlparse(href).query)
            if qs.get("uddg"):
                href = qs["uddg"][0]
        except Exception:
            pass
    # Bing wraps outbound links in /ck/a?...&u=a1<base64url>
    if "bing.com/ck/a" in href:
        try:
            raw = parse_qs(urlparse(href).query).get("u", [""])[0]
            if raw.startswith("a1"):
                pad = "=" * (-len(raw[2:]) % 4)
                href = base64.urlsafe_b64decode(raw[2:] + pad).decode("utf-8", "ignore")
        except Exception:
            pass
    if href.startswith("http://"):
        href = "https://" + href[7:]
    return href if href.startswith("https://") else ""


def _words(text: str) -> set:
    return set(re.findall(r"[a-z0-9]{3,}", (text or "").lower()))


def score(query: str, it: Dict[str, str]) -> float:
    q, body = _words(query), _words(it["title"] + " " + it["snippet"])
    overlap = len(q & body) / max(len(q), 1)
    bonus = {"wikipedia": 0.30, "simplewiki": 0.22, "google": 0.20,
             "bing": 0.10, "duckduckgo": 0.10, "webpages": 0.18}.get(it["source"], 0.0)
    return overlap * 2.0 + bonus + min(len(it["text"]) / 5000.0, 0.25)


# ---------------------------------------------------------------------------
# Individual platform adapters. Each returns (items, note).
# ---------------------------------------------------------------------------

def _google_news(q: str) -> Tuple[List[Dict[str, str]], str]:
    url = ("https://news.google.com/rss/search?q=" + quote(q) +
           "&hl=en-US&gl=US&ceid=US:en")
    root = ET.fromstring(fetch(url, 6.0))
    out = []
    for node in root.findall(".//item")[:6]:
        title = node.findtext("title") or ""
        link = node.findtext("link") or ""
        desc = strip_tags(node.findtext("description") or "")
        pub = node.findtext("pubDate") or ""
        if title and link:
            src = (node.findtext("source") or "Google News")
            out.append(item(title, link, (src + " · " + pub[:16] + " · " + desc)[:420],
                            "google", desc, "news"))
    return out, "Google News RSS"


def _google_books(q: str) -> Tuple[List[Dict[str, str]], str]:
    url = ("https://www.googleapis.com/books/v1/volumes?q=" + quote(q) +
           "&maxResults=3&printType=books")
    data = fetch_json(url, 6.0)
    out = []
    for doc in (data.get("items") or [])[:3]:
        v = doc.get("volumeInfo", {})
        title = v.get("title") or ""
        desc = strip_tags(v.get("description") or "")
        link = v.get("infoLink") or "https://books.google.com/"
        authors = ", ".join(v.get("authors") or [])[:60]
        if title:
            out.append(item(title, link, (authors + " · " + desc)[:420],
                            "google", desc, "book"))
    return out, "Google Books"


def _google_web(q: str) -> Tuple[List[Dict[str, str]], str]:
    # Google sometimes serves an anti-bot JavaScript page from a shared IP.
    # We try honestly, and report the block instead of faking results.
    try:
        page = fetch("https://www.google.com/search?q=" + quote(q) + "&hl=en&num=10", 5.0)
        if "enablejs" in page or "not redirected" in page:
            return [], "Google web search blocked by anti-bot check; Google News + Books used"
        blocks = re.findall(r'''<div[^>]+class="[^"]*g[^"]*".*?</div>\s*</div>''', page, re.S)
        out = []
        for b in blocks[:6]:
            m = re.search(r"<h3[^>]*>(.*?)</h3>", b, re.S)
            u = re.search(r"href=\"(https?://[^\"]+)\"", b)
            if m and u:
                out.append(item(strip_tags(m.group(1)), tidy_url(u.group(1)),
                                strip_tags(b), "google", strip_tags(b), "web"))
        return out, "Google web results"
    except Exception as exc:
        return [], "Google web search unavailable (" + type(exc).__name__ + ")"


def _wikipedia(q: str, simple: bool = False) -> Tuple[List[Dict[str, str]], str]:
    host = "simple.wikipedia.org" if simple else "en.wikipedia.org"
    url = ("https://" + host + "/w/api.php?action=query&generator=search&gsrsearch=" +
           quote(q) + "&gsrlimit=3&prop=extracts&exintro=1&explaintext=1&format=json&redirects=1")
    data = fetch_json(url, 7.0)
    out = []
    for page in (data.get("query", {}).get("pages") or {}).values():
        title = page.get("title") or ""
        extract = re.sub(r"\s+", " ", page.get("extract") or "").strip()
        if title and extract:
            link = "https://" + host + "/wiki/" + quote(title.replace(" ", "_"))
            out.append(item(title, link, extract[:420],
                            "simplewiki" if simple else "wikipedia", extract[:2400], "encyclopedia"))
    return out, "Simple English Wikipedia" if simple else "Wikipedia API"


def _duckduckgo(q: str) -> Tuple[List[Dict[str, str]], str]:
    page = fetch("https://html.duckduckgo.com/html/?q=" + quote(q), 6.0)
    blocks = re.findall(r'<div class="result results_links.*?(?=<div class="result results_links|</body>)',
                        page, re.S)
    out = []
    for b in blocks[:8]:
        a = re.search(r'<a[^>]*class="result__a"[^>]*href="([^"]+)"[^>]*>(.*?)</a>', b, re.S)
        if not a:
            continue
        url = tidy_url(a.group(1))
        title = strip_tags(a.group(2))
        sn = re.search(r'class="result__snippet"[^>]*>(.*?)</(?:a|div|span)>', b, re.S)
        snippet = strip_tags(sn.group(1)) if sn else ""
        if url and title:
            out.append(item(title, url, snippet, "duckduckgo", snippet, "web"))
    return out, "DuckDuckGo HTML"


def _bing(q: str) -> Tuple[List[Dict[str, str]], str]:
    page = fetch("https://www.bing.com/search?q=" + quote(q) + "&count=10", 6.0)
    blocks = re.findall(r'<li class="b_algo".*?</li>', page, re.S)
    out = []
    for b in blocks[:8]:
        a = re.search(r"<h2[^>]*>\s*<a[^>]*href=\"([^\"]+)\"[^>]*>(.*?)</a>", b, re.S)
        if not a:
            continue
        url = tidy_url(a.group(1))
        title = strip_tags(a.group(2))
        p = re.search(r"<p[^>]*>(.*?)</p>", b, re.S)
        snippet = strip_tags(p.group(1)) if p else ""
        if url and title:
            out.append(item(title, url, snippet, "bing", snippet, "web"))
    return out, "Bing web results"


def _wikidata(q: str) -> Tuple[List[Dict[str, str]], str]:
    url = ("https://www.wikidata.org/w/api.php?action=wbsearchentities&search=" +
           quote(q) + "&language=en&format=json&limit=3")
    data = fetch_json(url, 6.0)
    out = []
    for e in data.get("search", [])[:3]:
        desc = e.get("description") or ""
        if desc:
            out.append(item(e.get("label") or q,
                            e.get("concepturi") or "https://www.wikidata.org/",
                            desc, "wikidata", desc, "fact"))
    return out, "Wikidata entities"


def _stackoverflow(q: str) -> Tuple[List[Dict[str, str]], str]:
    url = ("https://api.stackexchange.com/2.3/search/advanced?order=desc&sort=relevance&q=" +
           quote(q) + "&site=stackoverflow&pagesize=3&filter=withbody")
    data = fetch_json(url, 6.0)
    out = []
    for qn in data.get("items", [])[:3]:
        body = strip_tags(qn.get("body") or "")
        out.append(item(qn.get("title") or "Stack Overflow answer",
                        qn.get("link") or "https://stackoverflow.com/",
                        body[:420], "stackoverflow", body[:2400], "code"))
    return out, "Stack Overflow Q&A"


def _openlibrary(q: str) -> Tuple[List[Dict[str, str]], str]:
    url = ("https://openlibrary.org/search.json?q=" + quote(q) +
           "&limit=3&fields=title,author_name,first_sentence,key")
    data = fetch_json(url, 6.0)
    out = []
    for d in data.get("docs", [])[:3]:
        title = d.get("title") or ""
        first = d.get("first_sentence") or ""
        if isinstance(first, list):
            first = first[0] if first else ""
        desc = (first + " Authors: " + ", ".join((d.get("author_name") or [])[:2])).strip()
        if title:
            out.append(item(title, "https://openlibrary.org" + (d.get("key") or ""),
                            desc[:420], "openlibrary", desc[:2400], "book"))
    return out, "Open Library catalogue"


def _github(q: str) -> Tuple[List[Dict[str, str]], str]:
    url = ("https://api.github.com/search/repositories?q=" + quote(q) +
           "&per_page=3&sort=stars")
    data = fetch_json(url, 6.0)
    out = []
    for r in data.get("items", [])[:3]:
        desc = r.get("description") or ""
        out.append(item(r.get("full_name") or "repository", r.get("html_url") or
                        "https://github.com/", desc, "github", desc, "code"))
    return out, "GitHub repositories"


def _read_pages(results: List[Dict[str, str]], limit: int = 2) -> Tuple[List[Dict[str, str]], str]:
    """Open the best non-encyclopedia result pages and read their real text."""
    skip = ("wikipedia.org", "google.com", "bing.com", "duckduckgo.com",
            "youtube.com", "twitter.com", "facebook.com", "reddit.com")
    picks: List[Dict[str, str]] = []
    for r in results:
        if not r.get("url") or any(x in r["url"] for x in skip):
            continue
        if r.get("kind") == "news":
            continue
        picks.append(r)
        if len(picks) >= limit:
            break
    out, ok = [], 0
    for r in picks:
        try:
            page = fetch(r["url"], 5.0)
            body = re.sub(r"<(script|style|nav|header|footer|aside)\b.*?</\1>", " ", page,
                          flags=re.S | re.I)
            paras = re.findall(r"<p[^>]*>(.*?)</p>", body, re.S | re.I)
            text = " ".join(strip_tags(p) for p in paras if len(strip_tags(p)) > 55)
            if len(text) < 220:
                text = strip_tags(body)
            if len(text) > 200:
                out.append(item(r["title"], r["url"], text[:420], "webpages",
                                text[:2400], "page"))
                ok += 1
        except Exception:
            continue
    return out, f"read {ok} page(s) in full"


# ---------------------------------------------------------------------------
# Orchestration
# ---------------------------------------------------------------------------


def _arxiv(q: str) -> Tuple[List[Dict[str, str]], str]:
    """Peer-reviewed preprints: the reference for physics, maths, CS and ML."""
    url = ("http://export.arxiv.org/api/query?search_query=all:%s"
           "&start=0&max_results=3&sortBy=relevance" % quote(q[:120]))
    body = fetch(url, timeout=7)
    out = []
    for m in re.finditer(r"<entry>(.*?)</entry>", body, re.S):
        block = m.group(1)
        title = re.search(r"<title>(.*?)</title>", block, re.S)
        summ = re.search(r"<summary>(.*?)</summary>", block, re.S)
        link = re.search(r"<id>(.*?)</id>", block, re.S)
        if not title:
            continue
        out.append(item(re.sub(r"\s+", " ", title.group(1)).strip(),
                        (link.group(1).strip() if link else ""),
                        re.sub(r"\s+", " ", (summ.group(1) if summ else "")).strip()[:400],
                        "arxiv", "preprint"))
    return out, ("%d papers" % len(out)) if out else "no papers matched"


def _crossref(q: str) -> Tuple[List[Dict[str, str]], str]:
    """Crossref: the DOI registry, so a claim can be traced to a publication."""
    url = ("https://api.crossref.org/works?query=%s&rows=3&select=title,"
           "URL,abstract,container-title" % quote(q[:120]))
    data = fetch_json(url, timeout=7) or {}
    out = []
    for it in ((data.get("message") or {}).get("items") or [])[:3]:
        titles = it.get("title") or []
        if not titles:
            continue
        out.append(item(titles[0], it.get("URL", ""),
                        (it.get("abstract") or "")[:400],
                        "crossref", (it.get("container-title") or [""])[0][:60]))
    return out, ("%d records" % len(out)) if out else "no records matched"


def _openalex(q: str) -> Tuple[List[Dict[str, str]], str]:
    """OpenAlex: open index of 250M+ scholarly works."""
    url = "https://api.openalex.org/works?search=%s&per-page=3" % quote(q[:120])
    data = fetch_json(url, timeout=7) or {}
    out = []
    for w in (data.get("results") or [])[:3]:
        t = w.get("title") or w.get("display_name")
        if not t:
            continue
        inv = w.get("abstract_inverted_index") or {}
        abstract = ""
        if inv:
            pairs = sorted((pos, word) for word, ps in inv.items() for pos in ps)[:70]
            abstract = " ".join(word for _p, word in pairs)[:400]
        out.append(item(t, (w.get("doi") or w.get("id") or ""), abstract,
                        "openalex", "scholarly"))
    return out, ("%d works" % len(out)) if out else "no works matched"


def _hackernews(q: str) -> Tuple[List[Dict[str, str]], str]:
    """Hacker News: strong for tooling, releases and practitioner experience."""
    url = "https://hn.algolia.com/api/v1/search?query=%s&hitsPerPage=4" % quote(q[:120])
    data = fetch_json(url, timeout=6) or {}
    out = []
    for h in (data.get("hits") or [])[:4]:
        title = h.get("title") or h.get("story_title")
        if not title:
            continue
        link = h.get("url") or ("https://news.ycombinator.com/item?id=%s" % h.get("objectID"))
        text = h.get("story_text") or h.get("comment_text") or ""
        out.append(item(title, link, clean(strip_tags(text), 300), "hackernews",
                        "%s points" % (h.get("points") or 0)))
    return out, ("%d threads" % len(out)) if out else "no threads matched"


def _reddit(q: str) -> Tuple[List[Dict[str, str]], str]:
    """Reddit: real-world experience, clearly labelled as opinion, not fact.

    Reddit blocks a lot of datacenter traffic, so a 403 here is routine: it is
    reported as "unavailable from this network" rather than as an error, and
    the answer never pretends a thread was read when none was.
    """
    out = []
    data = {}
    for host in ("https://old.reddit.com", "https://www.reddit.com"):
        try:
            data = fetch_json(host + "/search.json?q=%s&limit=4&sort=relevance"
                              % quote(q[:120]), timeout=6) or {}
            if (data.get("data") or {}).get("children"):
                break
        except Exception:
            data = {}
    if not (data.get("data") or {}).get("children"):
        return [], "unavailable from this network"
    for ch in (((data.get("data") or {}).get("children")) or [])[:4]:
        d = ch.get("data") or {}
        title = d.get("title")
        if not title:
            continue
        out.append(item(title, "https://www.reddit.com" + (d.get("permalink") or ""),
                        clean(strip_tags(d.get("selftext") or ""), 260), "reddit",
                        "r/%s" % (d.get("subreddit") or "?")))
    return out, ("%d posts" % len(out)) if out else "no posts matched"


def _deepseek(q: str) -> Tuple[List[Dict[str, str]], str]:
    """DeepSeek (or any OpenAI-compatible model) as a second reasoning pass.

    Off unless RYZEK_AI_KEYS holds a key: without one there is nothing honest
    to show, and pretending otherwise would be a lie about the sources.
    """
    key, base, model = ai_endpoint("deepseek")
    if not key:
        return [], "no key set (RYZEK_AI_KEYS)"
    body = {"model": model, "temperature": 0.2, "max_tokens": 500,
            "messages": [{"role": "system",
                          "content": "Answer in plain English, factually, in under 120 words. "
                                     "No preamble."},
                         {"role": "user", "content": q}]}
    data = post_json(base.rstrip("/") + "/chat/completions", body, key, timeout=14) or {}
    text = ""
    try:
        text = data["choices"][0]["message"]["content"]
    except Exception:
        return [], "no answer returned"
    return [item("DeepSeek " + model + " - second opinion", base, clean(text, 600),
                 "deepseek", model)], "answered"


def _grok(q: str) -> Tuple[List[Dict[str, str]], str]:
    """Grok (xAI) - same OpenAI-compatible shape as DeepSeek."""
    key, base, model = ai_endpoint("grok")
    if not key:
        return [], "no key set (RYZEK_AI_KEYS)"
    body = {"model": model, "temperature": 0.2, "max_tokens": 500,
            "messages": [{"role": "system",
                          "content": "Answer factually in plain English under 120 words."},
                         {"role": "user", "content": q}]}
    data = post_json(base.rstrip("/") + "/chat/completions", body, key, timeout=14) or {}
    try:
        text = data["choices"][0]["message"]["content"]
    except Exception:
        return [], "no answer returned"
    return [item("Grok " + model + " - second opinion", base, clean(text, 600),
                 "grok", model)], "answered"


AI_ENDPOINTS = {
    "deepseek": {"env": "DEEPSEEK_API_KEY", "base": "https://api.deepseek.com",
                 "default_model": "deepseek-chat"},
    "grok": {"env": "GROK_API_KEY", "base": "https://api.x.ai/v1", "default_model": "grok-2-latest"},
}


def ai_endpoint(name: str) -> Tuple[str, str, str]:
    """Return (key, base_url, model) for an optional AI source.

    Keys live in the environment (RYZEK_AI_KEYS=deepseek=sk-...,grok=xai-...
    or the individual variables). If there is no key the source is simply
    absent from the answer - the app never claims a model it did not call.
    """
    spec = AI_ENDPOINTS[name]
    key = os.environ.get(spec["env"], "")
    base = os.environ.get(spec["env"].replace("_API_KEY", "_BASE_URL"), spec["base"])
    model = os.environ.get(spec["env"].replace("_API_KEY", "_MODEL"), spec["default_model"])
    if not key:
        packed = os.environ.get("RYZEK_AI_KEYS", "")
        for part in packed.split(","):
            if "=" in part:
                k, v = part.split("=", 1)
                if k.strip().lower() == name:
                    key = v.strip()
    return key, base, model


def post_json(url: str, body: Dict[str, Any], key: str,
              timeout: float = 12.0) -> Any:
    data = json.dumps(body).encode("utf-8")
    req = urlrequest.Request(url, data=data, method="POST", headers={
        "Content-Type": "application/json", "Authorization": "Bearer " + key,
        "Accept": "application/json", "User-Agent": UA})
    try:
        with urlrequest.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read().decode("utf-8", "replace"))
    except Exception:
        return {}


ADAPTERS: List[Tuple[str, str, Callable[[str], Tuple[List[Dict[str, str]], str]]]] = [
    ("google_news", "google", _google_news),
    ("google_books", "google", _google_books),
    ("google_web", "google", _google_web),
    ("wikipedia", "wikipedia", _wikipedia),
    ("simplewiki", "simplewiki", lambda q: _wikipedia(q, simple=True)),
    ("bing", "bing", _bing),
    ("duckduckgo", "duckduckgo", _duckduckgo),
    ("wikidata", "wikidata", _wikidata),
    ("openlibrary", "openlibrary", _openlibrary),
    ("stackoverflow", "stackoverflow", _stackoverflow),
    ("github", "github", _github),
    ("arxiv", "arxiv", _arxiv),
    ("crossref", "crossref", _crossref),
    ("openalex", "openalex", _openalex),
    ("hackernews", "hackernews", _hackernews),
    ("reddit", "reddit", _reddit),
    ("deepseek", "deepseek", _deepseek),
    ("grok", "grok", _grok),
]

CODE_WORDS = re.compile(r"\b(python|code|program|function|script|error|bug|api|javascript|"
                        r"java|sql|algorithm|library|class|debug|regex)\b", re.I)


def _cache_path(query: str) -> Path:
    key = hashlib.sha1(query.strip().lower().encode("utf-8")).hexdigest()[:20]
    return CACHE_DIR / (key + ".json")


def _cache_get(query: str) -> Optional[Dict[str, Any]]:
    p = _cache_path(query)
    try:
        if p.exists() and time.time() - p.stat().st_mtime < CACHE_TTL:
            d = json.loads(p.read_text(encoding="utf-8"))
            if d.get("query") == query.strip().lower():
                return d
    except Exception:
        pass
    return None


def _cache_put(query: str, data: Dict[str, Any]) -> None:
    try:
        _cache_path(query).write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    except Exception:
        pass


def gather(query: str, limit: int = 12, read_pages: bool = True,
           timeout: float = 8.0) -> Dict[str, Any]:
    """Query every platform at once. Always returns; never raises.

    Returns {"items": [...], "status": [...], "platforms": [...], "query": str}
    """
    global LAST_STATUS, LAST_QUERY, LAST_TIME
    q = re.sub(r"\s+", " ", (query or "").strip())[:220]
    if not q or len(q) < 3:
        return {"items": [], "status": [], "platforms": PLATFORMS, "query": q}
    cached = _cache_get(q)
    if cached:
        with _STATUS_LOCK:
            LAST_STATUS, LAST_QUERY, LAST_TIME = cached["status"], q, time.time()
        return cached

    codeish = bool(CODE_WORDS.search(q))
    todo = [a for a in ADAPTERS if a[0] != "stackoverflow" or codeish]
    todo = [a for a in todo if a[0] != "github" or codeish]
    # optional AI second opinions: skip the network call when no key is set
    todo = [a for a in todo if a[0] not in AI_ENDPOINTS or ai_endpoint(a[0])[0]]

    results: List[Dict[str, str]] = []
    notes: Dict[str, str] = {}
    counts: Dict[str, int] = {}
    errors: Dict[str, str] = {}

    def run(entry):
        name, platform, fn = entry
        try:
            got, note = fn(q)
            return name, platform, got, note, ""
        except Exception as exc:
            return name, platform, [], "", type(exc).__name__

    with ThreadPoolExecutor(max_workers=8) as pool:
        futures = [pool.submit(run, e) for e in todo]
        try:
            for f in as_completed(futures, timeout=timeout + 2):
                name, platform, got, note, err = f.result()
                if got:
                    results.extend(got)
                    counts[platform] = counts.get(platform, 0) + len(got)
                    notes[name] = note
                elif err:
                    errors[name] = err
                elif note:
                    notes[name] = note
        except Exception:
            pass

    # Read the best pages in full, using the results we already have.
    if read_pages and results:
        try:
            pages, note = _read_pages(sorted(results, key=lambda r: -score(q, r))[:8])
            if pages:
                results.extend(pages)
                counts["webpages"] = len(pages)
                notes["webpages"] = note
        except Exception:
            pass

    # De-duplicate by URL and by very similar titles, then rank.
    seen_urls, seen_titles, items = set(), set(), []
    for r in sorted(results, key=lambda r: -score(q, r)):
        u = r.get("url") or ""
        key = re.sub(r"[^a-z0-9]", "", r["title"].lower())[:55]
        if (u and u in seen_urls) or key in seen_titles:
            continue
        if not r.get("snippet") and not r.get("text"):
            continue
        seen_urls.add(u)
        seen_titles.add(key)
        items.append(r)
        if len(items) >= limit:
            break

    status = []
    for p in PLATFORMS:
        pid = p["id"]
        n = counts.get(pid, 0)
        reason = ""
        if not n:
            relevant = [e for k, e in errors.items() if k.startswith(pid)]
            reason = ("unavailable: " + relevant[0]) if relevant else (
                "only used for coding questions" if pid in ("stackoverflow", "github") and not codeish
                else "no usable results")
        detail = "; ".join(v for k, v in notes.items()
                           if k == pid or (pid == "google" and k.startswith("google_"))
                           or (pid == "webpages" and k == "webpages"))
        status.append({"id": pid, "label": p["label"], "icon": p["icon"],
                       "color": p["color"], "desc": p["desc"],
                       "ok": bool(n), "count": n, "note": reason, "detail": detail[:190]})

    data = {"items": items, "status": status, "platforms": PLATFORMS, "query": q,
            "cached": False, "notes": notes}
    with _STATUS_LOCK:
        LAST_STATUS, LAST_QUERY, LAST_TIME = status, q, time.time()
    _cache_put(q, data)
    return data


def last_status() -> Dict[str, Any]:
    with _STATUS_LOCK:
        return {"query": LAST_QUERY, "at": LAST_TIME, "status": list(LAST_STATUS),
                "platforms": PLATFORMS}


def source_lines(items: List[Dict[str, str]], n: int = 6) -> str:
    """Markdown bullets with real links, used at the end of an answer."""
    lines = []
    for it in items[:n]:
        if not it.get("url"):
            continue
        label = {"google": "Google", "wikipedia": "Wikipedia",
                 "simplewiki": "Simple Wikipedia", "bing": "Bing",
                 "duckduckgo": "DuckDuckGo", "wikidata": "Wikidata",
                 "stackoverflow": "Stack Overflow", "openlibrary": "Open Library",
                 "github": "GitHub", "webpages": "Web page"}.get(it["source"], "Web")
        lines.append(f"- [{it['title']}]({it['url']}) — {label} · {it['domain'] or 'online source'}")
    return "\n".join(lines)


def _sentences_of(body: str) -> List[str]:
    got = []
    for raw in re.split(r"(?<=[.!?])\s+", body):
        s = re.sub(r"\s+", " ", raw).strip()
        s = re.sub(r"^[\-\*\d\.\)\s]+", "", s)
        if not (40 <= len(s) <= 310) or s.startswith("="):
            continue
        if not re.search(r"[a-zA-Z]{4}", s):
            continue
        if not s.endswith((".", "!", "?")):
            s += "."
        got.append(s)
    return got


def material_sentences(items: List[Dict[str, str]], max_items: int = 10) -> List[str]:
    """Real sentences from live pages for the essay/article writing desk.

    A definition from Wikipedia / Simple Wikipedia is placed first so an essay
    opens by saying what the topic IS, not with an opinion from a news result.
    """
    chosen = items[:max_items]
    lead: List[str] = []
    for it in chosen:
        if it.get("source") not in ("wikipedia", "simplewiki", "wikidata"):
            continue
        for s in _sentences_of(it.get("text") or it.get("snippet") or ""):
            if re.search(r"\b(refers to|is a |is the |are a |are the |means |describes )", s, re.I):
                lead.append(s)
                break
        if lead:
            break
    rest: List[str] = []
    for it in chosen:
        rest.extend(_sentences_of(it.get("text") or it.get("snippet") or ""))
    out = lead + rest
    seen, res = set(), []
    for s in out:
        k = s[:65].lower()
        if k in seen:
            continue
        seen.add(k)
        res.append(s)
        if len(res) >= 26:
            break
    return res
