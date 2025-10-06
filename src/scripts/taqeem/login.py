import asyncio
from browser import closeBrowser, wait_for_element, set_page, get_page
from navigation import post_login_navigation

async def startLogin(page, email, password):
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

        otp_field = await wait_for_element(page, "#otp, input[type='tel'], input[name='otp'], #emailCode, #verificationCode", 15)
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


async def submitOtp(page, otp):
    if not page:
        return {"status": "FAILED", "error": "No login session", "recoverable": False}

    try:
        otp_input = await wait_for_element(page, "#otp, input[type='tel'], input[name='otp'], #emailCode, #verificationCode", 30)
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

        error_message = await wait_for_element(page, "#input-error-otp-code", timeout=5)
        print("Looking for error message")
        if error_message:
            print("Error message found: ", error_message.text)
            return {"status": "OTP_FAILED", "message": "Try Again", "recoverable": True}

        nav_result = await post_login_navigation(page)
        if nav_result["status"] == "SUCCESS":
            return {"status": "SUCCESS", "recoverable": True}

        dashboard = await wait_for_element(page, "#dashboard, .dashboard, .welcome, [class*='success']", 15)
        if dashboard:
            return {"status": "SUCCESS", "warning": "Navigation skipped (dashboard found)", "recoverable": True}

        await closeBrowser()
        return {**nav_result, "recoverable": False}

    except Exception as e:
        await closeBrowser()
        return {"status": "FAILED", "error": str(e), "recoverable": False}
