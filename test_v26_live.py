#!/usr/bin/env python3
"""End-to-end test of v2.6 accounts, memory and answer quality on a live server."""

import json
import sys
import urllib.error
import urllib.request

BASE = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8000"
fails = []


def req(path, data=None, token=None, method=None):
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = "Bearer " + token
    body = json.dumps(data).encode() if data is not None else None
    r = urllib.request.Request(BASE + path, data=body, headers=headers,
                               method=method or ("POST" if body else "GET"))
    try:
        with urllib.request.urlopen(r, timeout=120) as resp:
            return resp.status, json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        try:
            return e.code, json.loads(e.read().decode())
        except Exception:
            return e.code, {}


def check(name, ok, detail=""):
    print(("  PASS  " if ok else "  FAIL  ") + name + (("  -> " + str(detail)) if detail else ""))
    if not ok:
        fails.append(name)


print("\nv2.6 accounts + memory + answers\n")

# 1. the root page is the login screen when there is no token
with urllib.request.urlopen(BASE + "/", timeout=20) as r:
    html = r.read().decode()
check("signed-out visit shows the login page", "Sign in" in html and "Create account" in html,
      "%d bytes" % len(html))
check("login page keeps the credit line", "Rasakh Mohsin" in html and "Ryzek_20" in html)

# 2. chat is refused without a token
status, body = req("/api/chat", {"message": "hi"})
check("chat refused without a token", status == 401, status)

# 3. wrong password
status, body = req("/api/login", {"username": "ryzek", "password": "nope"})
check("wrong password rejected", status == 401 and body.get("code") == "bad_credentials",
      body.get("error"))

# 4. author login
status, body = req("/api/login", {"username": "ryzek", "password": "ryzek20"})
check("author can sign in", status == 200 and body.get("ok"), status)
author = body.get("token", "")
check("author role is 'author'", (body.get("user") or {}).get("role") == "author")
check("password is not returned", "pass_hash" not in json.dumps(body))

# 5. me + sessions
status, me = req("/api/me", token=author)
check("/api/me works", status == 200 and me.get("user", {}).get("username") == "ryzek")
status, sess = req("/api/sessions", token=author)
check("sessions listed for the account", status == 200, len(sess.get("sessions", [])))

# 6. create a normal account
import random
uname = "test%04d" % random.randint(1, 9999)
status, body = req("/api/signup", {"username": uname, "password": "secret123",
                                   "display_name": "Test Person"})
check("normal account created", status == 200 and body.get("ok"), status)
user_token = body.get("token", "")
check("normal account role is 'user'", (body.get("user") or {}).get("role") == "user")

# 7. duplicate + weak password + bad username rules
status, body = req("/api/signup", {"username": uname, "password": "secret123"})
check("duplicate username refused", status == 400 and body.get("code") == "taken")
status, body = req("/api/signup", {"username": "ab", "password": "secret123"})
check("short username refused", status == 400 and body.get("code") == "bad_username")
status, body = req("/api/signup", {"username": "okname1", "password": "123"})
check("short password refused", status == 400 and body.get("code") == "bad_password")

# 8. the two accounts cannot see each other's chats
status, s1 = req("/api/sessions", {"x": 1}, token=author)
status, s2 = req("/api/sessions", token=user_token)
ids_author = {s["id"] for s in s1.get("sessions", [])}
ids_user = {s["id"] for s in s2.get("sessions", [])}
check("accounts have separate chat lists", not (ids_author & ids_user),
      "author %d / user %d" % (len(ids_author), len(ids_user)))

# 9. memory: tell it things, then ask
status, c1 = req("/api/chat", {"message": "hi, my name is Ayesha and I live in Lahore"},
                 token=user_token)
check("chat works with an account", status == 200 and len(c1.get("reply", "")) > 200,
      "%d chars" % len(c1.get("reply", "")))
sid = c1.get("session_id")
req("/api/chat", {"message": "my favourite colour is green", "session_id": sid},
    token=user_token)
status, mem = req("/api/memory", token=user_token)
keys = {f["key"] for f in mem.get("facts", [])}
check("name remembered", "name" in keys, sorted(keys))
check("city remembered", "city" in keys, sorted(keys))
check("favourite remembered", any(k.startswith("favourite") for k in keys), sorted(keys))

status, c2 = req("/api/chat", {"message": "what is my name?", "session_id": sid},
                 token=user_token)
reply = c2.get("reply", "")
check("recalls the name when asked", "Ayesha" in reply, reply[:120].replace("\n", " "))

status, c3 = req("/api/chat", {"message": "what do you remember about me?", "session_id": sid},
                 token=user_token)
check("memory summary lists the facts", "Lahore" in c3.get("reply", ""),
      c3.get("reply", "")[:100].replace("\n", " "))

# 10. the other account must not see those memories
status, other = req("/api/chat", {"message": "what is my name?"}, token=author)
check("memories are per-account", "Ayesha" not in other.get("reply", ""),
      other.get("reply", "")[:90].replace("\n", " "))

# 11. understanding is reported
check("understanding returned to the UI",
      isinstance(c2.get("understanding"), dict) and c2["understanding"].get("intent"),
      c2.get("understanding"))

# 12. answer quality on the four problem questions
quality = [
    ("what is the difference between affect and effect", ["verb", "noun"], ["greenhouse", "black hole"]),
    ("why does my phone battery drain fast", ["battery"], ["Put It Down", "Health Protection Agency"]),
    ("how do i get better at coding", ["language", "practice"], ["piggybacking"]),
    ("what do you remember about me?", ["remember"], []),
]
for q, must, mustnot in quality:
    status, body = req("/api/chat", {"message": q}, token=user_token)
    text = (body.get("reply") or "").lower()
    ok_must = all(m.lower() in text for m in must)
    ok_mustnot = not any(m.lower() in text for m in mustnot)
    check("answer is on-topic: %s" % q[:44], status == 200 and ok_must and ok_mustnot,
          "%d chars | must:%s mustnot:%s" % (len(text), ok_must, ok_mustnot))

# 13. author-only account list
status, users = req("/api/users", token=author)
check("author can list accounts", status == 200 and len(users.get("users", [])) >= 2,
      len(users.get("users", [])))
status, users2 = req("/api/users", token=user_token)
check("normal accounts cannot list accounts", status == 403, status)

# 14. author can delete a normal account, but not themselves
status, users = req("/api/users", token=author)
target = next((u for u in users["users"] if u["username"] == uname), None)
if target:
    status, body = req("/api/users/delete", {"id": target["id"]}, token=author)
    check("author can delete a normal account", body.get("ok") is True)
status, body = req("/api/users/delete", {"id": 1}, token=author)
check("author account cannot be deleted", body.get("ok") is False)

# 15. logout invalidates the token
req("/api/logout", {}, token=user_token)
status, body = req("/api/me", token=user_token)
check("token stops working after sign out", status == 401, status)

print()
if fails:
    print("RESULT: %d checks failed" % len(fails))
    for f in fails:
        print("   -", f)
    sys.exit(1)
print("RESULT: all checks passed")
