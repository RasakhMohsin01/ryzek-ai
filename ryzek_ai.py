#!/usr/bin/env python3
"""
Ryzek AI v2 - entry point: HTTP server, streaming API, terminal chat.

  python ryzek_ai.py                 # web UI  -> http://localhost:8000
  python ryzek_ai.py --cli           # terminal chat
  python ryzek_ai.py --port 8080     # different port
  python ryzek_ai.py --selftest      # offline sanity checks

Engine: ryzek_core.py   |   UI: ryzek_ui.py   |   Knowledge: knowledge_base.json
Everything is Python standard library. No pip install.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any, Dict, Optional
from urllib.parse import parse_qs, urlparse

import ryzek_auth as auth
import ryzek_core as core
from ryzek_ui import INDEX_HTML, LOGIN_HTML

NAME = core.NAME
VERSION = core.VERSION


class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"
    server_version = f"RyzekAI/{VERSION}"

    # ------------------------------------------------------------------ utils
    def log_message(self, fmt: str, *args: Any) -> None:
        sys.stderr.write("[%s] %s\n" % (self.log_date_time_string(), fmt % args))

    @property
    def ryzek(self) -> core.Ryzek:
        return self.server.ryzek  # type: ignore[attr-defined]

    def _send(self, code: int, body: str, ctype: str = "application/json; charset=utf-8",
              cookies: Any = None) -> None:
        data = body.encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store, no-cache, must-revalidate, max-age=0")
        self.send_header("Pragma", "no-cache")
        self.send_header("Expires", "0")
        for cookie in list(cookies or []) + getattr(self, "_cookies", []):
            self.send_header("Set-Cookie", cookie)
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(data)

    # -- v2.6.1: the session token is also kept in a cookie, because a page
    # navigation cannot send an Authorization header. Header still wins.
    def _cookie(self, token: str, days: int = 30) -> str:
        return ("ryzek_token=%s; Path=/; Max-Age=%d; HttpOnly; SameSite=Lax"
                % (token, days * 86400))

    def _clear_cookie(self) -> str:
        return "ryzek_token=; Path=/; Max-Age=0; HttpOnly; SameSite=Lax"

    def _me(self) -> Optional[Dict[str, Any]]:
        token = auth.bearer(self.headers)
        return self.ryzek.auth.current(token) if token else None

    def _json(self, code: int, obj: Dict[str, Any], cookies: Any = None) -> None:
        self._send(code, json.dumps(obj, ensure_ascii=False), cookies=cookies)

    def _start_stream(self) -> None:
        self.send_response(200)
        self.send_header("Content-Type", "application/x-ndjson; charset=utf-8")
        self.send_header("Transfer-Encoding", "chunked")
        self.send_header("Cache-Control", "no-cache, no-transform")
        self.send_header("X-Accel-Buffering", "no")
        self.end_headers()

    def _chunk(self, obj: Dict[str, Any]) -> None:
        data = (json.dumps(obj, ensure_ascii=False) + "\n").encode("utf-8")
        try:
            self.wfile.write(f"{len(data):X}\r\n".encode("ascii"))
            self.wfile.write(data)
            self.wfile.write(b"\r\n")
            self.wfile.flush()
        except (BrokenPipeError, ConnectionResetError, OSError):
            pass

    def _end_stream(self) -> None:
        try:
            self.wfile.write(b"0\r\n\r\n")
            self.wfile.flush()
        except (BrokenPipeError, ConnectionResetError, OSError):
            pass
        self.close_connection = True

    def _body(self) -> Dict[str, Any]:
        try:
            length = int(self.headers.get("Content-Length") or 0)
            return json.loads(self.rfile.read(length) or b"{}")
        except Exception:
            return {}

    # ------------------------------------------------------------------- GET
    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        path, qs = parsed.path, parse_qs(parsed.query)

        if path in ("/", "/index.html"):
            url_token = (qs.get("t") or [""])[0]
            me = self._me()
            if me is None and url_token:
                me = self.ryzek.auth.current(url_token)
                if me is not None:
                    self._cookies = [self._cookie(url_token)]
            if me is None:
                if (qs.get("loop") or [""])[0] == "1":
                    self._send(200, LOGIN_HTML.replace("{{NAME}}", NAME)
                               .replace("{{VERSION}}", VERSION), "text/html; charset=utf-8",
                               cookies=[self._clear_cookie()])
                    return
                self._send(200, LOGIN_HTML.replace("{{NAME}}", NAME)
                           .replace("{{VERSION}}", VERSION), "text/html; charset=utf-8")
                return
            page = (INDEX_HTML.replace("{{NAME}}", NAME).replace("{{VERSION}}", VERSION)
                    .replace("{{USER}}", json.dumps(self.ryzek.auth.public(me))))
            self._send(200, page, "text/html; charset=utf-8")
        elif path in ("/login", "/signin"):
            self._send(200, LOGIN_HTML.replace("{{NAME}}", NAME)
                       .replace("{{VERSION}}", VERSION), "text/html; charset=utf-8")
        elif path in ("/api/me", "/me"):
            me = self._me()
            if me is None:
                self._json(401, {"ok": False, "error": "not signed in"})
                return
            self._json(200, {"ok": True, "user": self.ryzek.auth.public(me),
                             "memory": self.ryzek.memory.stats(me["id"]),
                             "logins": self.ryzek.auth.db.recent_logins(me["id"], 6)})
        elif path in ("/api/memory", "/memory"):
            me = self._me()
            if me is None:
                self._json(401, {"ok": False, "error": "not signed in"})
                return
            rows = [dict(r) for r in self.ryzek.memory.all_facts(me["id"], limit=60)]
            qa = self.ryzek.memory.recent_questions(me["id"], limit=40)
            self._json(200, {"ok": True, "facts": rows, "questions": qa,
                             "stats": self.ryzek.memory.stats(me["id"])})
        elif path == "/api/author/overview":
            me = self._me()
            if me is None:
                self._json(401, {"ok": False, "error": "not signed in"})
                return
            if me["role"] != "author":
                self._json(403, {"ok": False, "error": "Author account only."})
                return
            db = self.ryzek.auth.db
            users = db.every_user_activity()
            for u in users:
                u.pop("created_at", None)
            try:
                sessions = self.ryzek.store.list(me["id"])
            except Exception:
                sessions = []
            asked = self.ryzek.memory.stats(me["id"])
            self._json(200, {
                "ok": True,
                "stats": db.stats(),
                "users": users,
                "guard": self.ryzek.guard.summary(),
                "mine": {"chats": len(sessions), "facts": asked.get("facts", 0),
                         "questions": asked.get("questions", 0)},
                "server": {"version": VERSION,
                           "topics": int(self.ryzek.status().get("topics", 0)
                                         if isinstance(self.ryzek.status(), dict) else 0)},
            })
            return
        elif path == "/api/author/users":
            me = self._me()
            if me is None or me["role"] != "author":
                self._json(403 if me else 401, {"ok": False,
                                                "error": "Author account only."})
                return
            self._json(200, {"ok": True, "users": self.ryzek.auth.db.every_user_activity()})
            return
        elif path in ("/api/users", "/users"):
            token = auth.bearer(self.headers)
            me = self.ryzek.auth.current(token) if token else None
            if me is None or me.get("role") != "author":
                self._json(403, {"ok": False, "error": "author account required"})
                return
            self._json(200, {"ok": True, "users": self.ryzek.auth.db.list_users()})
        elif path in ("/api/status", "/status"):
            self._json(200, self.ryzek.status())
        elif path == "/api/settings":
            self._json(200, {"ok": True, "settings": self.ryzek.config.get(),
                             "defaults": core.q.default_opts(),
                             "depth": self.ryzek.config.depth})
        elif path == "/api/about":
            self._json(200, {"text": core.about_text(), "creator": core.CREATOR,
                             "handle": core.CREATOR_HANDLE,
                             "instagram": core.CREATOR_INSTAGRAM,
                             "url": core.CREATOR_INSTAGRAM_URL,
                             "version": VERSION})
        elif path in ("/api/web", "/web"):
            self._json(200, {"ok": True, "online": core.ONLINE,
                             "platforms": core.web.PLATFORMS,
                             "last": core.web.last_status()})
        elif path in ("/health", "/healthz"):
            self._json(200, {"ok": True, "name": NAME, "version": VERSION})
        elif path == "/api/sessions":
            me = self._me()
            if me is None:
                self._json(401, {"ok": False, "error": "not signed in"})
                return
            self._json(200, {"sessions": self.ryzek.store.list(owner=me["id"])})
        elif path == "/api/session":
            me = self._me()
            if me is None:
                self._json(401, {"ok": False, "error": "not signed in"})
                return
            sid = (qs.get("id") or [""])[0]
            s = self.ryzek.store.get(sid or None, owner=me["id"])
            self._json(200, {"id": s.id, "title": s.title, "count": len(s.messages),
                             "messages": s.messages, "user_name": s.user_name or "",
                             "facts": list(s.facts.values())[-6:],
                             "last_topic": s.last_topic or ""})
        elif path == "/api/knowledge":
            with core.INDEX_LOCK:
                titles = [t["title"] for t in core.KB]
            cached = []
            for p in sorted(core.LEARNED_DIR.glob("*.json"),
                            key=lambda x: x.stat().st_mtime, reverse=True)[:40]:
                try:
                    cached.append(json.loads(p.read_text(encoding="utf-8"))["title"])
                except Exception:
                    pass
            self._json(200, {"topics": titles, "cached": cached,
                             "chunks": len(core.INDEX.chunks), "tools": sorted(core.TOOL_REGISTRY)})
        elif path == "/favicon.ico":
            self._send(204, "")
        else:
            self._json(404, {"error": "not found", "hint": "try / or /api/status"})

    # ------------------------------------------------------------------ POST
    def do_POST(self) -> None:
        path = urlparse(self.path).path
        payload = self._body()

        if path == "/api/account/password":
            me = self._me()
            if me is None:
                self._json(401, {"ok": False, "error": "not signed in"})
                return
            current = str(payload.get("current") or "")
            new = str(payload.get("password") or payload.get("new") or "")
            try:
                if self.ryzek.auth.db.verify(me["username"], current) is None:
                    self._json(400, {"ok": False,
                                     "error": "Your current password is not correct."})
                    return
                self.ryzek.auth.db.set_password(me["id"], new)
                user, fresh = self.ryzek.auth.login(
                    me["username"], new, ip=self.client_address[0],
                    ua=self.headers.get("User-Agent", ""))
                self._json(200, {"ok": True, "token": fresh,
                                 "user": self.ryzek.auth.public(user)},
                           cookies=[self._cookie(fresh)])
            except auth.AuthError as exc:
                self._json(400, {"ok": False, "error": exc.message})
            return
        if path in ("/api/login", "/login"):
            username = str(payload.get("username", ""))
            password = str(payload.get("password", ""))
            try:
                user, token = self.ryzek.auth.login(
                    username, password, ip=self.client_address[0],
                    ua=self.headers.get("User-Agent", ""))
            except auth.AuthError as exc:
                self._json(401, {"ok": False, "error": exc.message, "code": exc.code})
                return
            self._json(200, {"ok": True, "token": token,
                             "user": self.ryzek.auth.public(user),
                             "memory": self.ryzek.memory.stats(user["id"])},
                       cookies=[self._cookie(token)])
            return
        if path in ("/api/signup", "/signup", "/api/register"):
            username = str(payload.get("username", ""))
            password = str(payload.get("password", ""))
            display = str(payload.get("display_name") or username)
            device = str(payload.get("device") or "")[:64]
            ip = self.client_address[0]
            try:
                self.ryzek.guard.check(device, ip)
                user, token = self.ryzek.auth.signup(
                    username, password, display, ip=ip,
                    ua=self.headers.get("User-Agent", ""))
                self.ryzek.guard.record(user["id"], device, ip,
                                        self.headers.get("User-Agent", ""))
            except auth.AuthError as exc:
                self._json(400, {"ok": False, "error": exc.message, "code": exc.code})
                return
            self._json(200, {"ok": True, "token": token,
                             "user": self.ryzek.auth.public(user)},
                       cookies=[self._cookie(token)])
            return
        if path in ("/api/logout", "/logout"):
            token = auth.bearer(self.headers) or str(payload.get("token", ""))
            self.ryzek.auth.logout(token)
            self._json(200, {"ok": True}, cookies=[self._clear_cookie()])
            return
        if path == "/api/memory/forget":
            me = self._me()
            if me is None:
                self._json(401, {"ok": False, "error": "not signed in"})
                return
            key = str(payload.get("key", "")).strip()
            if key:
                self.ryzek.memory.forget_fact(me["id"], key)
            else:
                self.ryzek.memory.clear(me["id"])
            self._json(200, {"ok": True, "stats": self.ryzek.memory.stats(me["id"])})
            return
        if path == "/api/author/reset":
            me = self._me()
            if me is None or me["role"] != "author":
                self._json(403 if me else 401, {"ok": False,
                                                "error": "Author account only."})
                return
            target = int(payload.get("user_id") or 0)
            if target and target == int(me["id"]):
                self._json(400, {"ok": False,
                                 "error": "Use Settings to change your own password."})
                return
            new_pw = auth.random_password()
            try:
                self.ryzek.auth.db.set_password(target, new_pw)
            except Exception:
                self._json(400, {"ok": False, "error": "That account could not be found."})
                return
            self._json(200, {"ok": True, "password": new_pw})
            return
        if path in ("/api/users/delete", "/api/users/role", "/api/users/disable",
                    "/api/users/password"):
            token = auth.bearer(self.headers)
            me = self.ryzek.auth.current(token) if token else None
            if me is None or me.get("role") != "author":
                self._json(403, {"ok": False, "error": "author account required"})
                return
            target = int(payload.get("id") or 0)
            try:
                if path.endswith("delete"):
                    ok = self.ryzek.auth.db.delete_user(target)
                    self._json(200, {"ok": ok})
                elif path.endswith("role"):
                    self.ryzek.auth.db.set_role(target, str(payload.get("role", "user")))
                    self._json(200, {"ok": True})
                elif path.endswith("disable"):
                    self.ryzek.auth.db.set_disabled(target, bool(payload.get("disabled")))
                    self._json(200, {"ok": True})
                else:
                    self.ryzek.auth.db.set_password(target, str(payload.get("password", "")))
                    self._json(200, {"ok": True})
            except auth.AuthError as exc:
                self._json(400, {"ok": False, "error": exc.message})
            return

        if path == "/api/chat":
            self._handle_chat(payload, stream=False)
        elif path == "/api/chat/stream":
            self._handle_chat(payload, stream=True)
        elif path == "/api/settings":
            body = payload.get("settings")
            if not isinstance(body, dict):
                body = {k: v for k, v in payload.items() if k != "session_id"}
            settings = self.ryzek.config.replace(body)
            depth = payload.get("depth")
            if isinstance(depth, str) and depth in core.DEPTHS:
                self.ryzek.config.set_depth(depth)
            self._json(200, {"ok": True, "settings": settings,
                             "depth": self.ryzek.config.depth})
        elif path == "/api/settings/reset":
            self._json(200, {"ok": True, "settings": self.ryzek.config.reset(),
                             "depth": self.ryzek.config.depth})
        elif path == "/api/reset":
            s = self.ryzek.store.get(payload.get("session_id"))
            s.clear()
            self.ryzek.store.save()
            self._json(200, {"ok": True, "id": s.id})
        elif path == "/api/sessions":
            me2 = self._me()
            if me2 is None:
                self._json(401, {"ok": False, "error": "not signed in"})
                return
            s = self.ryzek.store.get(owner=me2["id"])
            self.ryzek.store.save()
            self._json(200, {"id": s.id, "title": s.title})
        elif path == "/api/sessions/delete":
            ok = self.ryzek.store.delete(str(payload.get("id", "")))
            self._json(200, {"ok": ok})
        elif path == "/api/sessions/rename":
            self.ryzek.store.rename(str(payload.get("id", "")), str(payload.get("title", "")))
            self._json(200, {"ok": True})
        elif path == "/api/web/search":
            query = str(payload.get("query", "")).strip()
            if not query:
                self._json(400, {"error": "query required"})
                return
            data = core.web.gather(query, limit=int(payload.get("limit", 10) or 10))
            self._json(200, {"ok": True, "query": query, "items": data["items"],
                             "status": data["status"], "platforms": core.web.PLATFORMS})
        elif path == "/api/learn":
            topic = str(payload.get("topic", "")).strip()
            if not topic:
                self._json(400, {"error": "topic required"})
                return
            s = self.ryzek.store.get(payload.get("session_id"))
            opts = core.q.default_opts(self.ryzek.config.get())
            ctx = core.Context(session=s, online=payload.get("online", True),
                               depth=self.ryzek.config.depth(), opts=opts)
            reply = core.learn_topic(topic, ctx)
            self._json(200, {"reply": reply, "sources": ctx.sources,
                             "topics": len(core.KB), "cached": core.cached_count()})
        else:
            self._json(404, {"error": "not found"})

    def _handle_chat(self, payload: Dict[str, Any], stream: bool) -> None:
        message = str(payload.get("message") or "")
        me = self._me()
        if me is None:
            self._json(401, {"ok": False, "error": "Please sign in first.",
                             "login": True})
            return
        session = self.ryzek.store.get(payload.get("session_id"), owner=me["id"])
        depth = payload.get("depth")
        if depth not in core.DEPTHS:
            depth = self.ryzek.config.depth
        online = payload.get("online", True)
        if not isinstance(online, bool):
            online = True
        opts = payload.get("settings")
        if not isinstance(opts, dict):
            opts = None

        if stream:
            self._start_stream()
            self._chunk({"type": "step", "label": "Request received", "detail": message[:70]})
            try:
                self.ryzek.respond(message, session, depth=depth, online=online,
                                   opts=opts, user=me,
                                   emit=lambda ev: self._chunk(ev))
            except Exception as exc:
                fallback_ctx = core.Context(session=session, opts=opts or {})
                self._chunk({"type": "final", "reply": core.q.finalize_answer(
                             "## Something interrupted that answer\n\n" +
                             core.long_scaffold(message, fallback_ctx) +
                             f"\n\nTechnical detail: `{type(exc).__name__}: {exc}`",
                             message, opts or {}),
                             "engine": "offline", "note": "", "sources": [], "trace": [],
                             "elapsed": 0, "session_id": session.id, "title": session.title,
                             "web": []})
            self._end_stream()
            return

        reply = self.ryzek.respond(message, session, depth=depth, online=online,
                                   opts=opts, user=me)
        self._json(200, {
            "reply": reply.text, "engine": reply.engine, "note": reply.note,
            "trace": reply.trace, "sources": reply.sources, "elapsed": reply.elapsed,
            "session_id": reply.session_id, "depth": reply.depth, "title": session.title,
            "web": reply.web_status, "name": NAME,
            "understanding": reply.understanding,
        })

    def do_HEAD(self) -> None:
        self.do_GET()

    def do_OPTIONS(self) -> None:
        self.send_response(204)
        self.send_header("Allow", "GET, POST, OPTIONS")
        self.send_header("Content-Length", "0")
        self.end_headers()


def serve(port: int) -> None:
    httpd = ThreadingHTTPServer(("0.0.0.0", port), Handler)
    httpd.daemon_threads = True
    httpd.ryzek = core.Ryzek()  # type: ignore[attr-defined]
    st = httpd.ryzek.status()
    print()
    print("  ╔══════════════════════════════════════════════════════════╗")
    print(f"  ║   {NAME} v{VERSION}  -  advanced research agent           ║")
    print("  ╚══════════════════════════════════════════════════════════╝")
    print(f"  Web UI  : http://localhost:{port}   (also in the live preview)")
    print(f"  Engine  : {st['engine']}  ({st['model']})")
    print(f"  Knowledge: {st['topics']} topics, {st['cached']} cached articles, {st['chunks']} chunks")
    print(f"  Tools   : {st['tools']}   |   Live research: {'on' if st['online'] else 'off'}")
    if st["engine"] == "offline":
        print("  Tip     : set RYZEK_API_KEY for the tool-calling LLM brain (see README.md)")
    print()
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n  Ryzek AI signing off.")
    finally:
        httpd.server_close()


def chat_cli() -> None:
    r = core.Ryzek()
    s = r.store.get()
    st = r.status()
    print()
    print("  ╔══════════════════════════════════════════════════════════╗")
    print(f"  ║   {NAME} v{VERSION}  -  terminal mode                       ║")
    print("  ╚══════════════════════════════════════════════════════════╝")
    print(f"  Engine: {st['engine']} | {st['topics']} topics | {st['tools']} tools | /help /exit")
    print("  Every question gets a detailed, sourced answer.\n")
    while True:
        try:
            q = input("  You: ").strip()
        except (EOFError, KeyboardInterrupt):
            print(f"\n  {NAME}: Catch you later.\n")
            break
        if q.lower() in ("/exit", "exit", "quit", "bye"):
            print(f"\n  {NAME}: See you - bring the next hard question.\n")
            break
        t = time.time()
        rep = r.respond(q, s)
        print(f"\n  {NAME}  [{rep.engine} | {rep.depth} | {rep.elapsed}s | {len(rep.sources)} sources]")
        print("  " + "- " * 32)
        for line in rep.text.splitlines():
            print("  " + line)
        if rep.trace:
            print("\n  Research steps: " + " -> ".join(x["label"] for x in rep.trace))
        if rep.sources:
            print("  Sources: " + ", ".join(x["title"] for x in rep.sources[:4]))
        print()
        _ = t


def selftest() -> None:
    core.ONLINE = False
    r = core.Ryzek()
    s = r.store.get("selftest")
    questions = ["hi", "what is 17% of 240?", "convert 10 km to miles",
                 "explain black holes in detail", "who are you",
                 "tell me a joke", "zindleflorp quantum blorf?"]
    print(f"\n  {NAME} v{VERSION} selftest (offline)\n")
    for q in questions:
        rep = r.respond(q, s)
        assert rep.text.strip(), f"empty answer for {q!r}"
        assert len(rep.text) > 200, f"answer too thin for {q!r}: {len(rep.text)} chars"
        print(f"  Q: {q[:44]:46s} -> {len(rep.text):5d} chars, {len(rep.trace)} steps, {rep.engine}")
    print("\n  All checks passed - every question got a detailed answer.\n")


def main() -> None:
    ap = argparse.ArgumentParser(description=f"{NAME} v{VERSION} - advanced Python AI agent")
    ap.add_argument("--cli", action="store_true", help="terminal chat instead of the browser")
    ap.add_argument("--port", type=int, default=int(os.environ.get("PORT", 8000)))
    ap.add_argument("--selftest", action="store_true", help="offline sanity checks and exit")
    args = ap.parse_args()
    if args.selftest:
        selftest()
    elif args.cli:
        chat_cli()
    else:
        serve(args.port)


if __name__ == "__main__":
    main()
