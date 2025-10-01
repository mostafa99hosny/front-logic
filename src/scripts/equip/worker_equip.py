import asyncio, sys, json, traceback
from login import startLogin, submitOtp
from browser import closeBrowser, get_browser
from formFiller import runFormFill
from formFiller2 import runFormFill2, check_incomplete_macros_after_creation, retryMacros
from addAssets import add_assets_to_report, check_incomplete_macros
# import sys 
# sys.stdout.reconfigure(encoding='utf-8')


async def _readline(loop):
    return await loop.run_in_executor(None, sys.stdin.readline)


async def worker():
    loop = asyncio.get_running_loop()

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
                # always start a new browser for login
                browser = await get_browser(force_new=True)
                page = await browser.get(
                    "https://sso.taqeem.gov.sa/realms/REL_TAQEEM/protocol/openid-connect/auth"
                    "?client_id=cli-qima-valuers&redirect_uri=https%3A%2F%2Fqima.taqeem.sa%2Fkeycloak%2Flogin%2Fcallback"
                    "&scope=openid&response_type=code"
                )
                result = await startLogin(page, cmd.get("email", ""), cmd.get("password", ""))

            elif action == "otp":
                browser = await get_browser()
                page = browser.main_tab
                result = await submitOtp(page, cmd.get("otp", ""))

            elif action == "formFill":
                browser = await get_browser()
                result = await runFormFill(browser, cmd.get("reportId", ""))

            elif action == "addAssets":
                browser = await get_browser()
                result = await add_assets_to_report(browser, cmd.get("reportId", ""))

            elif action == "check":
                browser = await get_browser()
                result = await check_incomplete_macros(browser, cmd.get("reportId", ""))

            elif action == "formFill2":
                browser = await get_browser()

                tabs_num = int(cmd.get("tabsNum", 3))  
                result = await runFormFill2(browser, cmd.get("reportId", ""), tabs_num=tabs_num)

            elif action == "checkMacros":
                browser = await get_browser()

                tabs_num = int(cmd.get("tabsNum", 3))
                result = await check_incomplete_macros_after_creation(browser, cmd.get("reportId", ""), browsers_num=tabs_num)

            elif action == "retryMacros":
                browser = await get_browser()

                tabs_num = int(cmd.get("tabsNum", 3))
                result = await retryMacros(browser, cmd.get("recordId", ""), tabs_num=tabs_num)

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
