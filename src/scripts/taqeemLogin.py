import asyncio
import json
import sys
import time
import nodriver as uc
import traceback

browser = None
page = None

async def wait_for_element(page, selector, timeout=30, check_interval=1):
    start_time = time.time()
    while time.time() - start_time < timeout:
        try:
            element = await page.query_selector(selector)
            if element:
                return element
        except Exception:
            pass
        await asyncio.sleep(check_interval)
    return None

async def startLogin(email, password):
    global browser, page

    # Launch browser if not already running
    if not browser:
        browser = await uc.start(
            headless=False,
            window_size=(1200, 800),
            user_data_dir=None
        )

    page = await browser.get(
        "https://sso.taqeem.gov.sa/realms/REL_TAQEEM/protocol/openid-connect/auth?client_id=cli-qima-valuers&redirect_uri=https%3A%2F%2Fqima.taqeem.sa%2Fkeycloak%2Flogin%2Fcallback&scope=openid&response_type=code"
    )

    await asyncio.sleep(5)

    try:
        await wait_for_element(page, "input, button, form", timeout=60)
    except Exception as e:
        return {"status": "FAILED", "error": f"Page load failed: {e}"}

    try:
        email_input = await wait_for_element(page, "#email, #username, input[type='email'], input[name='email']", timeout=30)
        if not email_input:
            return {"status": "FAILED", "error": "Email input not found"}
        await email_input.click()
        await email_input.send_keys(email)

        password_input = await wait_for_element(page, "#password, input[type='password'], input[name='password']", timeout=30)
        if not password_input:
            return {"status": "FAILED", "error": "Password input not found"}
        await password_input.click()
        await password_input.send_keys(password)

        login_btn = await wait_for_element(page, "#loginBtn, button[type='submit'], .login-button, input[type='submit']", timeout=30)
        if not login_btn:
            return {"status": "FAILED", "error": "Login button not found"}
        await login_btn.click()

        await asyncio.sleep(5)

        # Check OTP
        otp_field = await wait_for_element(page, "#otp, input[type='tel'], input[name='otp'], #emailCode, #verificationCode", timeout=15)
        if otp_field:
            # IMPORTANT: do NOT close browser; keep it for the OTP step
            return {"status": "OTP_REQUIRED"}

        dashboard = await wait_for_element(page, "#dashboard, .dashboard, .welcome, [class*='success']", timeout=10)
        if dashboard:
            return {"status": "LOGIN_SUCCESS"}

        return {"status": "FAILED", "error": "Unknown login state"}

    except Exception as e:
        return {"status": "FAILED", "error": str(e)}

async def submitOtp(otp):
    global page
    if page is None:
        return {"status": "FAILED", "error": "No login session"}

    try:
        # Use the specific ID from the HTML
        otp_input = await wait_for_element(page, "#emailCode", timeout=30)
        if not otp_input:
            return {"status": "FAILED", "error": "OTP input not found"}
        
        await otp_input.click()
        await otp_input.send_keys(otp)

        # Use the exact selector from the HTML - input with name="login" and type="submit"
        verify_btn = await wait_for_element(page, "input[name='login'][type='submit']", timeout=30)
        if not verify_btn:
            # Fallback to just name="login" in case the type attribute check fails
            verify_btn = await wait_for_element(page, "input[name='login']", timeout=5)
        
        if not verify_btn:
            return {"status": "FAILED", "error": "Verify button not found"}
        
        await verify_btn.click()

        await asyncio.sleep(5)

        # Check for successful login
        dashboard = await wait_for_element(page, "#dashboard, .dashboard, .welcome, [class*='success']", timeout=30)
        if dashboard:
            return {"status": "LOGIN_SUCCESS"}

        return {"status": "LOGIN_FAILED", "error": "OTP verification failed"}

    except Exception as e:
        return {"status": "FAILED", "error": str(e)}

async def closeBrowser():
    global browser, page
    if browser:
        try:
            await browser.stop()
        except Exception:
            pass
        finally:
            browser = None
            page = None

# -------- Persistent Worker Loop (NDJSON over stdin) --------

async def _readline(loop):
    # Read a line from stdin in a thread to avoid blocking the event loop
    return await loop.run_in_executor(None, sys.stdin.readline)

async def worker():
    loop = asyncio.get_running_loop()
    while True:
        try:
            line = await _readline(loop)
            if not line:
                # stdin closed by parent; shut down gracefully
                await closeBrowser()
                break

            line = line.strip()
            if not line:
                continue

            try:
                cmd = json.loads(line)
                action = cmd.get("action")
                if action == "login":
                    email = cmd.get("email") or ""
                    password = cmd.get("password") or ""
                    result = await startLogin(email, password)
                    print(json.dumps(result), flush=True)

                elif action == "otp":
                    otp = cmd.get("otp") or ""
                    result = await submitOtp(otp)
                    print(json.dumps(result), flush=True)

                elif action == "close":
                    await closeBrowser()
                    print(json.dumps({"status": "CLOSED"}), flush=True)

                else:
                    print(json.dumps({"status": "FAILED", "error": f"Unknown action: {action}"}), flush=True)

            except StopIteration:
                # Explicitly catch this Python 3.12+ error
                print(json.dumps({"status": "FAILED", "error": "Unexpected StopIteration in coroutine"}), flush=True)
            except Exception as e:
                tb = traceback.format_exc()
                print(json.dumps({"status": "FAILED", "error": str(e), "traceback": tb}), flush=True)

        except Exception as outer:
            tb = traceback.format_exc()
            print(json.dumps({"status": "FAILED", "error": str(outer), "traceback": tb}), flush=True)
            await closeBrowser()
            break

if __name__ == "__main__":
    asyncio.run(worker())
