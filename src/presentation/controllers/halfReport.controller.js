const { spawn } = require("child_process");
const path = require("path");
const AppError = require("../../shared/utils/appError");
const extractAssetData = require("../../application/taqeem/extractAssetData.uc.js");
const reportDataExtract = require("../../application/taqeem/reportDataExtract.uc.js");
const { getAssetsByUserIdUC } = require("../../application/reports/getAssetsByUserId.uc.js");
const {getHalfReportsByUserIdUC} = require("../../application/reports/getHalfReportsByUserId.uc.js");

let pyWorker = null;
let stdoutBuffer = "";
const pending = [];

// --- Ensure Python Worker ---
function ensurePyWorker() {
  if (pyWorker && !pyWorker.killed) return pyWorker;

  const isWin = process.platform === "win32";
  const venvPython = isWin
    ? path.join(__dirname, "../../../.venv/Scripts/python.exe")
    : path.join(__dirname, "../../../.venv/bin/python");

  const scriptPath = path.join(__dirname, "../../scripts/equip/worker_equip.py");
  const scriptDir = path.dirname(scriptPath); // folder containing the script

  pyWorker = spawn(venvPython, [scriptPath], {
    cwd: scriptDir, // ✅ use the folder containing the script
  });

  pyWorker.on("spawn", () => console.log("[PY] Worker spawned"));

  pyWorker.stdout.on("data", (data) => {
    stdoutBuffer += data.toString();
    let lines = stdoutBuffer.split(/\r?\n/);
    stdoutBuffer = lines.pop() || "";

    for (const line of lines) {
      if (!line.trim()) continue;

      let parsed;
      try {
        parsed = JSON.parse(line);
      } catch (e) {
        console.error("[PY] Invalid JSON line:", line);
        continue;
      }

      const handlers = pending.filter((req) => req.handler && typeof req.handler === "function");
      if (handlers.length) {
        handlers.forEach((req) => {
          try { req.handler(parsed); } catch (err) { console.error("[PY] Handler error:", err); }
        });
      } else {
        console.warn("[PY] Received response with no pending handler:", parsed);
      }
    }
  });

  pyWorker.stderr.on("data", (data) => console.error(`[PY STDERR] ${data.toString()}`));
  pyWorker.on("close", (code, signal) => {
    console.log(`[PY] Worker exited (code=${code}, signal=${signal})`);
    while (pending.length) {
      const req = pending.shift();
      req.reject(new AppError("Python worker exited unexpectedly", 500));
    }
    pyWorker = null;
    stdoutBuffer = "";
  });

  return pyWorker;
}

// --- Send Command to Worker ---
function sendCommand(cmdObj) {
  const py = ensurePyWorker();
  return new Promise((resolve, reject) => {
    const responses = [];
    let isComplete = false;

    const responseHandler = (data) => {
      responses.push(data);
      const finalStatuses = ["FORM_FILL_SUCCESS", "FAILED", "FATAL", "CLOSED", "SUCCESS", "OTP_REQUIRED", "LOGIN_SUCCESS"];
      if (finalStatuses.includes(data.status) && !isComplete) {
        isComplete = true;
        const index = pending.findIndex((req) => req.handler === responseHandler);
        if (index !== -1) pending.splice(index, 1);
        resolve(responses);
      }
    };

    const errorHandler = (err) => { if (!isComplete) { isComplete = true; reject(err); } };
    pending.push({ handler: responseHandler, reject: errorHandler });

    try { py.stdin.write(JSON.stringify(cmdObj) + "\n"); }
    catch (e) {
      const index = pending.findIndex((req) => req.handler === responseHandler);
      if (index !== -1) pending.splice(index, 1);
      reject(new AppError("Failed to send command to Python worker", 500));
    }
  });
}

// --- Close Worker ---
async function closeWorker() {
  if (!pyWorker) return;
  try { await sendCommand({ action: "close" }); } catch (e) { console.error("[closeWorker] sendCommand error:", e); }
  finally { try { pyWorker.kill("SIGTERM"); } catch (e) { console.error("[closeWorker] kill error:", e); } pyWorker = null; }
}

// --- Controller 1: Login / OTP / Navigation ---
const loginOrOtp = async (req, res, next) => {
  const { email, password, otp } = req.body;
  try {
    let payload;
    if (otp) payload = { action: "otp", otp };
    else if (email && password) payload = { action: "login", email, password };
    else return res.status(400).json({ success: false, message: "Email/password or OTP required" });

    const responses = await sendCommand(payload);
    res.json(responses[responses.length - 1] || { status: "UNKNOWN_RESPONSE" });
  } catch (err) {
    console.error("[loginOrOtp] error:", err);
    next(err instanceof AppError ? err : new AppError(String(err), 500));
  }
};

// --- Controller 2: Form Fill ---
const fillHalfReportForm = async (req, res, next) => {
  const { baseData } = req.body;
  const excelFilePath = req.files?.excel?.[0]?.path;
  const pdfFilePaths = req.files?.pdfs?.map(f => f.path) || [];

  try {
    if (!excelFilePath) return res.status(400).json({ success: false, message: "Excel file is required" });

    const result = await extractAssetData(excelFilePath, pdfFilePaths[0], baseData);
    if (result.status !== "SUCCESS") return res.status(400).json({ success: false, message: result.error });

    const responses = await sendCommand({ action: "formFill", reportId: result.data._id });

    res.json({
      success: true,
      status: "SAVED",
      data: result.data,
      automation: responses[responses.length - 1],
      message: "Report saved and automation executed.",
    });
  } catch (err) {
    console.error("[fillHalfReportForm] error:", err);
    next(err instanceof AppError ? err : new AppError(String(err), 500));
  }
};
const fillReportForm2 = async (req, res, next) => {
  const { id } = req.body;
  let tabsNum = parseInt(req.body.tabsNum, 10);
  if (isNaN(tabsNum) || tabsNum < 1) tabsNum = 3; 

  try {
    const response = await sendCommand({ action: "formFill2", reportId: id, tabsNum });
    res.json(response);
  } catch (err) {
    console.error("[fillReportForm2] error:", err);
    next(err instanceof AppError ? err : new AppError(String(err), 500));
  }
};

const reportDataExtraction = async (req, res, next) => {
  const excelFilePath = req.files?.excel?.[0]?.path;
  const pdfFilePaths  = req.files?.pdfs?.[0]?.path;
  const userId = req.user.userId;
  try {
    const result = await reportDataExtract(excelFilePath, pdfFilePaths, userId);
    if (result.status !== "SUCCESS") return res.status(400).json({
      success: false,
      message: result.message
    });

    res.json({
      success: true,
      status: "SAVED",
      data: result.data,
      message: "Report saved.",
    });
  } catch (err) {
    console.error("[reportDataExtract] error:", err);
    next(err instanceof AppError ? err : new AppError(String(err), 500));
  }
};

const extractExistingReportData = async (req, res, next) => {
  const { reportId } = req.body;
  const userId = req.user.userId;
  const excelFilePath = req.files?.excel?.[0]?.path;

  try {
    if (!excelFilePath) return res.status(400).json({ success: false, message: "Excel file is required" });

    const result = await extractAssetData(excelFilePath, null, null, { mode: "assetData", reportId, userId });
    if (result.status !== "SUCCESS") return res.status(400).json({
      success: false,
      message: result.error,
      summary: result.summary,
      highlights: result.highlights
    });

    res.json({
      success: true,
      status: "SAVED",
      data: result.data,
      message: "Assets added to report.",
    });

  } catch (err) {
    console.error("[addAssetsToReport] error:", err);
    next(err instanceof AppError ? err : new AppError(String(err), 500));
  }
}

const addAssetsToReport = async (req, res, next) => {
  const { reportId } = req.body;

  try {
    const responses = await sendCommand({ action: "addAssets", reportId });
    res.json(responses || { status: "UNKNOWN_RESPONSE" });

  } catch (err) {
    console.error("[addAssetsToReport] error:", err);
    next(err instanceof AppError ? err : new AppError(String(err), 500));
  }
};

const checkAssets = async (req, res, next) => {
  const { reportId } = req.body;
  try {
    const responses = await sendCommand({ action: "check", reportId });
    res.json(responses || { status: "UNKNOWN_RESPONSE" });

  } catch (err) {
    console.error("[checkAssets] error:", err);
    next(err instanceof AppError ? err : new AppError(String(err), 500));
  }
};

const getAssetsByUserId = async (req, res, next) => {
  try {
    const userId = req.user.userId;
    const assets = await getAssetsByUserIdUC(userId);
    res.status(200).json(assets);
  } catch (err) {
    console.error("[getAssetsByUserId] error:", err);
    next(err instanceof AppError ? err : new AppError(String(err), 500));
  }
};

const getHalfReportsByUserId = async (req, res, next) => {
  try {
    const userId = req.user.userId;
    const reports = await getHalfReportsByUserIdUC(userId);
    res.status(200).json(reports);
  } catch (err) {
    console.error("[getHalfReportsByUserId] error:", err);
    next(err instanceof AppError ? err : new AppError(String(err), 500));
  }
};

module.exports = {
  loginOrOtp,
  fillHalfReportForm,
  fillReportForm2,
  reportDataExtraction,
  extractExistingReportData,
  getHalfReportsByUserId,
  getAssetsByUserId,
  addAssetsToReport,
  checkAssets,
  sendCommand,
  closeWorker,
};
