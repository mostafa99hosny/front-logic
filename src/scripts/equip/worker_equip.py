import asyncio, sys, json, traceback
from login import startLogin, submitOtp
from browser import closeBrowser, get_browser
from formFiller import runFormFill
from addAssets import add_assets_to_report   


# --- Helpers ---
async def _readline(loop):
    return await loop.run_in_executor(None, sys.stdin.readline)

# --- Worker ---
async def worker():
    loop = asyncio.get_running_loop()
    browser = await get_browser()

    # Start on login page (first tab)
    page = await browser.get(
        "https://sso.taqeem.gov.sa/realms/REL_TAQEEM/protocol/openid-connect/auth"
        "?client_id=cli-qima-valuers&redirect_uri=https%3A%2F%2Fqima.taqeem.sa%2Fkeycloak%2Flogin%2Fcallback"
        "&scope=openid&response_type=code"
    )

    while True:
        line = await _readline(loop)
        if not line:
            await closeBrowser()
            break

        try:
            cmd = json.loads(line.strip())
        except json.JSONDecodeError:
            print(json.dumps({"status": "FAILED", "error": "Invalid JSON"}), flush=True)
            continue

        try:
            action = cmd.get("action")

            if action == "login":
                result = await startLogin(page, cmd.get("email", ""), cmd.get("password", ""))

            elif action == "otp":
                result = await submitOtp(page, cmd.get("otp", ""))

            elif action == "formFill":
                result = await runFormFill(browser, cmd.get("reportId", ""))

            elif action == "addAssets":
                # same here, let add_assets manage its own tab(s)
                result = await add_assets_to_report(browser, cmd.get("reportId", ""))

            elif action == "close":
                await closeBrowser()
                result = {"status": "CLOSED"}

            else:
                result = {"status": "FAILED", "error": f"Unknown action: {action}"}

            print(json.dumps(result), flush=True)

        except Exception as e:
            tb = traceback.format_exc()
            print(json.dumps({"status": "FAILED", "error": str(e), "traceback": tb}), flush=True)
            await closeBrowser()
            break


if __name__ == "__main__":
    asyncio.run(worker())
