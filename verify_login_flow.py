"""Browser test of the v2.6.1 login flow (the loop that froze the page)."""

import asyncio
import json
import sys

from playwright.async_api import async_playwright

BASE = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8000"
results = {}
console = []


async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True, args=["--no-sandbox"])
        ctx = await browser.new_context(viewport={"width": 1440, "height": 900})
        page = await ctx.new_page()
        page.on("console", lambda m: console.append(m.type + ": " + m.text[:160]))
        page.on("pageerror", lambda e: console.append("pageerror: " + str(e)[:160]))

        navigations = []
        page.on("framenavigated", lambda f: navigations.append(f.url) if f == page.main_frame else None)

        # 1. first visit -> login page
        await page.goto(BASE + "/", wait_until="networkidle")
        results["login_page_shown"] = await page.locator("#card").count() == 1
        results["no_app_on_login"] = await page.locator("#messageList").count() == 0

        # 2. sign in with the author account
        await page.fill("#username", "ryzek")
        await page.fill("#password", "ryzek20")
        await page.click("#submit")
        try:
            await page.wait_for_selector("#messageList", timeout=15000)
        except Exception:
            results["landed_in_app"] = False
        results["landed_in_app"] = await page.locator("#messageList").count() == 1

        # 3. the page must settle: count navigations for 3 seconds
        await page.wait_for_timeout(1000)
        nav_before = len(navigations)
        await page.wait_for_timeout(2500)
        results["navigations_while_idle"] = len(navigations) - nav_before
        results["no_loop"] = results["navigations_while_idle"] == 0

        # 4. reload: cookie keeps us signed in
        await page.reload(wait_until="networkidle")
        results["reload_stays_in_app"] = await page.locator("#messageList").count() == 1

        # 5. account panel shows the author account and memory
        results["account_button"] = await page.locator("#acctBtn").count() == 1
        name = (await page.locator("#acctName").inner_text()).strip()
        results["account_name"] = name
        await page.click("#acctBtn")
        await page.wait_for_timeout(900)
        results["drawer_open"] = await page.locator("#acctDrawer.on").count() == 1
        results["author_section"] = await page.locator("#adminSection").is_visible()
        await page.screenshot(path="/home/user/ryzek-ai/v26_account.png")
        await page.click("#acctClose")
        await page.wait_for_timeout(400)

        # 6. ask a question and confirm the understanding chip + an answer
        await page.fill("#input", "what is the difference between affect and effect")
        await page.click("#sendBtn")
        await page.wait_for_selector("#messageList .msg.bot", timeout=90000)
        await page.wait_for_timeout(1200)
        results["answer_rendered"] = await page.locator("#messageList .msg.bot .bubble").count() >= 1
        results["understood_chip"] = await page.locator(".understood").count() >= 1
        body = await page.locator("#messageList .msg.bot .bubble").last.inner_text()
        results["answer_snippet"] = body[:160].replace("\n", " ")
        await page.screenshot(path="/home/user/ryzek-ai/v26_chat.png")

        # 7. sign out returns to login, and / is protected again
        await page.click("#acctBtn")
        await page.wait_for_timeout(600)
        await page.click("#signOut")
        await page.wait_for_timeout(1500)
        results["signed_out_to_login"] = await page.locator("#card").count() == 1
        await page.goto(BASE + "/", wait_until="networkidle")
        results["protected_after_signout"] = await page.locator("#card").count() == 1

        results["console_errors"] = [c for c in console if c.startswith("pageerror")
                                     or c.startswith("error")]
        await browser.close()

    print(json.dumps(results, indent=2))
    bad = [k for k in ("login_page_shown", "no_app_on_login", "landed_in_app", "no_loop",
                       "reload_stays_in_app", "account_button", "drawer_open", "author_section",
                       "answer_rendered", "understood_chip", "signed_out_to_login",
                       "protected_after_signout") if not results.get(k)]
    if bad or results["console_errors"]:
        print("FAILED:", bad, results["console_errors"])
        sys.exit(1)
    print("ALL BROWSER CHECKS PASSED")


asyncio.run(main())
