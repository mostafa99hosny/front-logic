from browser import wait_for_element

async def post_login_navigation(page):
    try:
        sidebar_link = await wait_for_element(page, "a[title='العقارات']", timeout=30)
        if not sidebar_link:
            return {"status": "FAILED", "error": "Sidebar item not found"}
        await sidebar_link.click()

        org_link = await wait_for_element(page, "a[href='https://qima.taqeem.sa/organization/show/137']", timeout=30)
        if not org_link:
            return {"status": "FAILED", "error": "Organization link not found"}
        await org_link.click()

        app_tab_btn = await wait_for_element(page, "#appTab-3", timeout=30)
        if not app_tab_btn:
            return {"status": "FAILED", "error": "App tab button not found"}
        await app_tab_btn.click()

        report_link = await wait_for_element(page, "a[href='https://qima.taqeem.sa/report/create/1/137']", timeout=30)
        if not report_link:
            return {"status": "FAILED", "error": "Report creation link not found"}
        await report_link.click()

        translate = await wait_for_element(page, "a[href='https://qima.taqeem.sa/setlocale/en']", timeout=30)
        if not translate:
            return {"status": "FAILED", "error": "Translate link not found"}
        await translate.click()

        return {"status": "SUCCESS"}

    except Exception as e:
        return {"status": "FAILED", "error": str(e)}
