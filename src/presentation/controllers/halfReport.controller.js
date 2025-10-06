const { spawn } = require("child_process");
const path = require("path");
const AppError = require("../../shared/utils/appError");
const extractAssetData = require("../../application/taqeem/extractAssetData.uc.js");
const reportDataExtract = require("../../application/taqeem/reportDataExtract.uc.js");
const { getAssetsByUserIdUC } = require("../../application/reports/getAssetsByUserId.uc.js");
const { getHalfReportsByUserIdUC } = require("../../application/reports/getHalfReportsByUserId.uc.js");

let pyWorker = null;
let stdoutBuffer = "";
const pending = new Map(); // {type: {resolve, reject, taskId?}}
const activeTasks = new Map(); // {reportId: taskId} - track active tasks by reportId

// --- Ensure Python Worker ---
function ensurePyWorker() {
  if (pyWorker && !pyWorker.killed) return pyWorker;

  const isWin = process.platform === "win32";
  const venvPython = isWin
    ? path.join(__dirname, "../../../.venv/Scripts/python.exe")
    : path.join(__dirname, "../../../.venv/bin/python");

  const scriptPath = path.join(__dirname, "../../scripts/equip/worker_equip.py");
  const scriptDir = path.dirname(scriptPath);

  pyWorker = spawn(venvPython, [scriptPath], { cwd: scriptDir });

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

      console.log("[PY] Response:", parsed);

      // Store taskId for reportId mapping when task starts
      if (parsed.status === "STARTED" && parsed.taskId && parsed.reportId) {
        activeTasks.set(parsed.reportId, parsed.taskId);
        console.log(`[TASK REGISTERED] reportId=${parsed.reportId}, taskId=${parsed.taskId}`);
        // Don't resolve promise yet - wait for final status
        continue;
      }

      // Immediate control responses
      if (["PAUSED", "RESUMED", "STOPPED"].includes(parsed.status)) {
        const handler = pending.get("control");
        if (handler) {
          handler.resolve(parsed);
          pending.delete("control");
        }
        
        if (parsed.status === "STOPPED" && parsed.reportId) {
          activeTasks.delete(parsed.reportId);
        }
        continue;
      }

      // Task completion responses
      const finalStatuses = ["SUCCESS", "FAILED", "CLOSED", "LOGIN_SUCCESS", "NOT_FOUND", "OTP_REQUIRED", "OTP_FAILED"];
      if (finalStatuses.includes(parsed.status)) {
        const handler = pending.get("task");
        if (handler) {
          handler.resolve(parsed);
          pending.delete("task");
        }
        
        // Cleanup active task
        if (parsed.reportId) {
          activeTasks.delete(parsed.reportId);
        }
      }
    }
  });

  pyWorker.stderr.on("data", (data) => console.error(`[PY STDERR] ${data.toString()}`));
  
  pyWorker.on("close", (code, signal) => {
    console.log(`[PY] Worker exited (code=${code}, signal=${signal})`);
    pending.forEach((handler) => handler.reject(new AppError("Python worker exited", 500)));
    pending.clear();
    pyWorker = null;
    stdoutBuffer = "";
  });

  return pyWorker;
}

// --- Send Command to Worker ---
function sendCommand(cmdObj, type = "task") {
  const py = ensurePyWorker();
  
  return new Promise((resolve, reject) => {
    const handler = { resolve, reject };
    pending.set(type, handler);

    try {
      py.stdin.write(JSON.stringify(cmdObj) + "\n");
    } catch (e) {
      pending.delete(type);
      reject(new AppError("Failed to send command to Python worker", 500));
    }

    // Timeout for control commands (should be instant)
    if (type === "control") {
      setTimeout(() => {
        if (pending.has(type)) {
          pending.delete(type);
          reject(new AppError("Control command timeout", 500));
        }
      }, 5000);
    }
  });
}

// --- Close Worker ---
async function closeWorker() {
  if (!pyWorker) return;
  try {
    await sendCommand({ action: "close" });
  } catch (e) {
    console.error("[closeWorker] error:", e);
  } finally {
    try {
      pyWorker.kill("SIGTERM");
    } catch (e) {
      console.error("[closeWorker] kill error:", e);
    }
    pyWorker = null;
  }
}

// --- Controllers ---

const loginOrOtp = async (req, res, next) => {
  const { email, password, otp } = req.body;
  try {
    let payload;
    if (otp) payload = { action: "otp", otp };
    else if (email && password) payload = { action: "login", email, password };
    else return res.status(400).json({ success: false, message: "Email/password or OTP required" });

    const response = await sendCommand(payload);
    res.json(response);
  } catch (err) {
    console.error("[loginOrOtp] error:", err);
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

const pause = async (req, res, next) => {
  try {
    const { id } = req.body;  // Get reportId from body
    const taskId = activeTasks.get(id);
    
    console.log(`[PAUSE] reportId=${id}, taskId=${taskId}, activeTasks=`, Array.from(activeTasks.entries()));
    
    const response = await sendCommand({ 
      action: "pause", 
      reportId: id,
      taskId 
    }, "control");
    res.json(response);
  } catch (err) {
    console.error("[pause] error:", err);
    next(err instanceof AppError ? err : new AppError(String(err), 500));
  }
};

const resume = async (req, res, next) => {
  try {
    const { id } = req.body;  // Get reportId from body
    const taskId = activeTasks.get(id);
    
    console.log(`[RESUME] reportId=${id}, taskId=${taskId}`);
    
    const response = await sendCommand({ 
      action: "resume", 
      reportId: id,
      taskId 
    }, "control");
    res.json(response);
  } catch (err) {
    console.error("[resume] error:", err);
    next(err instanceof AppError ? err : new AppError(String(err), 500));
  }
};

const stop = async (req, res, next) => {
  try {
    const { id } = req.body;  // Get reportId from body
    const taskId = activeTasks.get(id);
    
    console.log(`[STOP] reportId=${id}, taskId=${taskId}`);
    
    const response = await sendCommand({ 
      action: "stop", 
      reportId: id,
      taskId 
    }, "control");
    res.json(response);
  } catch (err) {
    console.error("[stop] error:", err);
    next(err instanceof AppError ? err : new AppError(String(err), 500));
  }
};

const checkMacros = async (req, res, next) => {
  const { id } = req.body;
  let tabsNum = parseInt(req.body.tabsNum, 10);
  if (isNaN(tabsNum) || tabsNum < 1) tabsNum = 3;

  try {
    const response = await sendCommand({ action: "checkMacros", reportId: id, tabsNum });
    res.json(response);
  } catch (err) {
    console.error("[checkMacros] error:", err);
    next(err instanceof AppError ? err : new AppError(String(err), 500));
  }
};

const retryMacros = async (req, res, next) => {
  const { id } = req.body;
  let tabsNum = parseInt(req.body.tabsNum, 10);
  if (isNaN(tabsNum) || tabsNum < 1) tabsNum = 3;

  try {
    const response = await sendCommand({ action: "retryMacros", recordId: id, tabsNum });
    res.json(response);
  } catch (err) {
    console.error("[retryMacros] error:", err);
    next(err instanceof AppError ? err : new AppError(String(err), 500));
  }
};

const reportDataExtraction = async (req, res, next) => {
  const excelFilePath = req.files?.excel?.[0]?.path;
  const pdfFilePaths = req.files?.pdfs?.[0]?.path;
  const userId = req.user.userId;
  
  try {
    const result = await reportDataExtract(excelFilePath, pdfFilePaths, userId);
    if (result.status !== "SUCCESS") {
      return res.status(400).json({ success: false, message: result.message });
    }
    res.json({ success: true, status: "SAVED", data: result.data, message: "Report saved." });
  } catch (err) {
    console.error("[reportDataExtract] error:", err);
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

const fillHalfReportForm = async (req, res, next) => {
  const { baseData } = req.body;
  const excelFilePath = req.files?.excel?.[0]?.path;
  const pdfFilePaths = req.files?.pdfs?.map(f => f.path) || [];

  try {
    if (!excelFilePath) {
      return res.status(400).json({ success: false, message: "Excel file is required" });
    }

    const result = await extractAssetData(excelFilePath, pdfFilePaths[0], baseData);
    if (result.status !== "SUCCESS") {
      return res.status(400).json({ success: false, message: result.error });
    }

    const response = await sendCommand({ action: "formFill", reportId: result.data._id });
    res.json({
      success: true,
      status: "SAVED",
      data: result.data,
      automation: response,
      message: "Report saved and automation executed.",
    });
  } catch (err) {
    console.error("[fillHalfReportForm] error:", err);
    next(err instanceof AppError ? err : new AppError(String(err), 500));
  }
};

const extractExistingReportData = async (req, res, next) => {
  const { reportId } = req.body;
  const userId = req.user.userId;
  const excelFilePath = req.files?.excel?.[0]?.path;

  try {
    if (!excelFilePath) {
      return res.status(400).json({ success: false, message: "Excel file is required" });
    }

    const result = await extractAssetData(excelFilePath, null, null, { 
      mode: "assetData", 
      reportId, 
      userId 
    });
    
    if (result.status !== "SUCCESS") {
      return res.status(400).json({
        success: false,
        message: result.error,
        summary: result.summary,
        highlights: result.highlights
      });
    }

    res.json({
      success: true,
      status: "SAVED",
      data: result.data,
      message: "Assets added to report.",
    });
  } catch (err) {
    console.error("[extractExistingReportData] error:", err);
    next(err instanceof AppError ? err : new AppError(String(err), 500));
  }
};

const addAssetsToReport = async (req, res, next) => {
  const { reportId } = req.body;

  try {
    const response = await sendCommand({ action: "addAssets", reportId });
    res.json(response);
  } catch (err) {
    console.error("[addAssetsToReport] error:", err);
    next(err instanceof AppError ? err : new AppError(String(err), 500));
  }
};

const checkAssets = async (req, res, next) => {
  const { reportId } = req.body;
  
  try {
    const response = await sendCommand({ action: "check", reportId });
    res.json(response);
  } catch (err) {
    console.error("[checkAssets] error:", err);
    next(err instanceof AppError ? err : new AppError(String(err), 500));
  }
};

module.exports = {
  loginOrOtp,
  fillHalfReportForm,
  fillReportForm2,
  addAssetsToReport,
  extractExistingReportData,
  retryMacros,
  reportDataExtraction,
  getHalfReportsByUserId,
  checkMacros,
  checkAssets,
  getAssetsByUserId,
  pause,
  resume,
  stop,
  sendCommand,
  closeWorker,
};