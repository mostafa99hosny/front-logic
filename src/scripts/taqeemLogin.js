const { chromium } = require("playwright");

let browser, page, context;

async function startLogin(email, password) {
  browser = await chromium.launch({
    headless: false,  
  });

  context = await browser.newContext();
  page = await context.newPage();

  await page.goto("https://sso.taqeem.gov.sa/", { waitUntil: "networkidle" });

  await page.fill("#email", email);
  await page.fill("#password", password);
  await page.click("#loginBtn");

  await page.waitForSelector("#otp", { timeout: 60000 });
  console.log("Waiting for OTP...");

  return { status: "OTP_REQUIRED" };
}

async function submitOtp(otp) {
  if (!page) throw new Error("No login session started!");

  await page.fill("#otp", otp);
  await page.click("#verifyOtpBtn");

  await page.waitForSelector("#dashboard", { timeout: 60000 });
  console.log("Login successful!");

  return { status: "LOGIN_SUCCESS" };
}

async function closeBrowser() {
  if (browser) {
    await browser.close();
    browser = null;
    page = null;
    context = null;
    console.log("Browser closed.");
  }
}

module.exports = {
  startLogin,
  submitOtp,
  closeBrowser,
};
