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


async def get_browser():
    global browser
    if browser is None:
        browser = await uc.start(headless=False, window_size=(1200, 800))
    return browser


async def startLogin(email, password):
    global browser, page

    browser = await get_browser()
    page = await browser.get(
        "https://sso.taqeem.gov.sa/realms/REL_TAQEEM/protocol/openid-connect/auth?client_id=cli-qima-valuers&redirect_uri=https%3A%2F%2Fqima.taqeem.sa%2Fkeycloak%2Flogin%2Fcallback&scope=openid&response_type=code"
    )

    try:
        email_input = await wait_for_element(page, "#username, input[type='email']", 30)
        if not email_input:
            await closeBrowser()
            return {"status": "FAILED", "error": "Email input not found", "recoverable": False}

        await email_input.send_keys(email)
        password_input = await wait_for_element(page, "input[type='password']", 30)
        if not password_input:
            await closeBrowser()
            return {"status": "FAILED", "error": "Password input not found", "recoverable": False}

        await password_input.send_keys(password)

        login_btn = await wait_for_element(page, "#kc-login", 30)
        if not login_btn:
            await closeBrowser()
            return {"status": "FAILED", "error": "Login button not found", "recoverable": False}

        await login_btn.click()
        await asyncio.sleep(5)

        otp_field = await wait_for_element(
            page,
            "#otp, input[type='tel'], input[name='otp'], #emailCode, #verificationCode",
            15
        )
        if otp_field:
            return {"status": "OTP_REQUIRED", "recoverable": True}

        dashboard = await wait_for_element(page, "#dashboard", 10)
        if dashboard:
            return {"status": "LOGIN_SUCCESS", "recoverable": True}

        await closeBrowser()
        return {"status": "FAILED", "error": "Unknown login state", "recoverable": False}

    except Exception as e:
        await closeBrowser()
        return {"status": "FAILED", "error": str(e), "recoverable": False}


async def submitOtp(otp):
    global page

    if not page:
        return {"status": "FAILED", "error": "No login session", "recoverable": False}

    try:
        otp_input = await wait_for_element(
            page,
            "#otp, input[type='tel'], input[name='otp'], #emailCode, #verificationCode",
            30
        )
        if not otp_input:
            await closeBrowser()
            return {"status": "FAILED", "error": "OTP input not found", "recoverable": False}

        await otp_input.click()
        await otp_input.send_keys(otp)

        verify_btn = None
        for sel in [
            "input[name='login'][type='submit']",
            "input[name='login']",
            "button[type='submit']",
            "button[name='login']",
            ".login-button",
            "input[type='submit']"
        ]:
            verify_btn = await wait_for_element(page, sel, timeout=3)
            if verify_btn:
                break

        if not verify_btn:
            await closeBrowser()
            return {"status": "FAILED", "error": "Verify button not found", "recoverable": False}

        await verify_btn.click()
        await asyncio.sleep(1)

        dashboard = await wait_for_element(page, "#dashboard, .dashboard, .welcome, [class*='success']", 15)

        nav_result = await post_login_navigation(page)
        if nav_result["status"] == "SUCCESS":
            return {"status": "SUCCESS", "recoverable": True}
        else:
            if dashboard:
                return {"status": "SUCCESS", "warning": "Navigation skipped (dashboard found)", "recoverable": True}

            await closeBrowser()
            return {**nav_result, "recoverable": False}

    except Exception as e:
        await closeBrowser()
        return {"status": "FAILED", "error": str(e), "recoverable": False}



async def post_login_navigation(page):
    try:
        sidebar_link = await wait_for_element(page, "a[title='العقارات']", timeout=30)
        if not sidebar_link:
            return {"status": "FAILED", "error": "Sidebar item not found"}
        await sidebar_link.click()

        org_link = await wait_for_element(
            page,
            "a[href='https://qima.taqeem.sa/organization/show/137']",
            timeout=30
        )
        if not org_link:
            return {"status": "FAILED", "error": "Organization link not found"}
        await org_link.click()

        app_tab_btn = await wait_for_element(page, "#appTab-3", timeout=30)
        if not app_tab_btn:
            return {"status": "FAILED", "error": "App tab button not found"}
        await app_tab_btn.click()

        report_link = await wait_for_element(
            page,
            "a[href='https://qima.taqeem.sa/report/create/1/137']",
            timeout=30
        )
        if not report_link:
            return {"status": "FAILED", "error": "Report creation link not found"}
        await report_link.click()

        translate = await wait_for_element(
            page,
            "a[href='https://qima.taqeem.sa/setlocale/en']",
            timeout=30
        )
        if not translate:
            return {"status": "FAILED", "error": "Translate link not found"}
        await translate.click()

        return {"status": "SUCCESS"}

    except Exception as e:
        return {"status": "FAILED", "error": str(e)}


async def closeBrowser():
    global browser, page
    if browser:
        try:
            await browser.stop()
        except Exception:
            pass
    browser = None
    page = None


async def _readline(loop):
    return await loop.run_in_executor(None, sys.stdin.readline)


async def worker():
    loop = asyncio.get_running_loop()
    while True:
        try:
            line = await _readline(loop)
            if not line:
                await closeBrowser()
                break

            line = line.strip()
            if not line:
                continue

            try:
                cmd = json.loads(line)
            except json.JSONDecodeError:
                print(json.dumps({"status": "FAILED", "error": "Invalid JSON"}), flush=True)
                continue

            action = cmd.get("action")
            try:
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

                elif action == "formFill":
                    file_path = cmd.get("file")
                    pdf_paths = cmd.get("pdfs")

                    try:
                        from scripts.taqeem.formFiller import extractData, fill_form
                        from scripts.taqeem.formSteps import form_steps

                        result = await extractData(file_path, pdf_paths)
                        if result["status"] != "SUCCESS":
                            print(json.dumps(result), flush=True)
                            continue

                        records = result["data"]
                        print(json.dumps({"status": "EXTRACTED_DATA", "data": records}), flush=True)

                        for record in records:
                            for step_num, step_config in enumerate(form_steps, 1):
                                is_last_step = (step_num == len(form_steps))
                                print(f"Processing step {step_num}...", flush=True)

                                await fill_form(
                                    page,
                                    record,
                                    step_config["field_map"],
                                    step_config["field_types"],
                                    is_last_step
                                )

                                if is_last_step:
                                    print(json.dumps({
                                        "status": "FORM_FILL_SUCCESS",
                                        "message": "Form submitted successfully",
                                        "recoverable": True
                                    }), flush=True)
                                    break

                    except Exception as e:
                        tb = traceback.format_exc()
                        print(json.dumps({"status": "FAILED", "error": str(e), "traceback": tb}), flush=True)

                else:
                    print(json.dumps({"status": "FAILED", "error": f"Unknown action: {action}"}), flush=True)

            except Exception as e:
                tb = traceback.format_exc()
                print(json.dumps({"status": "FAILED", "error": str(e), "traceback": tb}), flush=True)
                await closeBrowser()

        except Exception as outer:
            tb = traceback.format_exc()
            print(json.dumps({"status": "FATAL", "error": str(outer), "traceback": tb}), flush=True)
            await closeBrowser()
            continue


if __name__ == "__main__":
    asyncio.run(worker())
