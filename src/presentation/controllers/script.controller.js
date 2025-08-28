const { spawn } = require('child_process');
const path = require('path');
const AppError = require('../../shared/utils/appError');

const runPythonScript = (req, res, next) => {
  if (!req.files?.excel?.[0] || !req.files?.pdfs?.length) {
    return next(new AppError('Upload both Excel and at least one PDF file.', 400));
  }

  const excelPath = req.files.excel[0].path;
  const pdfPaths = req.files.pdfs.map(file => file.path);
  const scriptPath = path.join(__dirname, '../../scripts/dummy.py');
  const venvPython = process.env.PYTHON_PATH  || path.join(__dirname, '../../../.venv/bin/python');

  console.log("pdfPaths", pdfPaths);

  const args = [scriptPath, excelPath];
  const py = spawn(venvPython, args);

  let output = '';
  py.stdout.on('data', data => (output += data.toString()));
  py.stderr.on('data', data => console.error(`Python error: ${data}`));

  py.on('close', code => {
    if (code !== 0) {
      return next(new AppError(`Python script exited with code ${code}`, 500));
    }
    res.json({ success: true, output });
  });
};

let pyWorker = null;
let stdoutBuffer = '';
const pending = [];

function ensurePyWorker() {
  if (pyWorker && !pyWorker.killed) return pyWorker;

  const scriptPath = path.join(__dirname, '../../scripts/taqeemLogin.py');
  const venvPython = path.join(__dirname, '../../../.venv/bin/python');

  pyWorker = spawn(venvPython, [scriptPath], {
    cwd: path.join(__dirname, '../../scripts'),
  });

  pyWorker.on('spawn', () => console.log('[PY] Worker spawned'));

  pyWorker.stdout.on('data', (data) => {
    stdoutBuffer += data.toString();

    let lines = stdoutBuffer.split(/\r?\n/);
    stdoutBuffer = lines.pop() || '';

    for (const line of lines) {
      if (!line.trim()) continue;
      let parsed;
      try {
        parsed = JSON.parse(line);
      } catch (e) {
        console.error('[PY] Invalid JSON line:', line);
        const req = pending.shift();
        if (req) req.reject(new AppError('Invalid JSON from Python', 500));
        continue;
      }
      const req = pending.shift();
      if (req) req.resolve(parsed);
      else console.warn('[PY] Received response with no pending request:', parsed);
    }
  });

  pyWorker.stderr.on('data', (data) => {
    console.error(`[PY STDERR] ${data.toString()}`);
  });

  pyWorker.on('close', (code, signal) => {
    console.log(`[PY] Worker exited (code=${code}, signal=${signal})`);
    while (pending.length) {
      const req = pending.shift();
      req.reject(new AppError('Python worker exited unexpectedly', 500));
    }
    pyWorker = null;
    stdoutBuffer = '';
  });

  return pyWorker;
}

function sendCommand(cmdObj) {
  const py = ensurePyWorker();
  return new Promise((resolve, reject) => {
    pending.push({ resolve, reject });
    try {
      py.stdin.write(JSON.stringify(cmdObj) + '\n');
    } catch (e) {
      pending.pop();
      reject(new AppError('Failed to send command to Python worker', 500));
    }
  });
}

async function closeWorker() {
  if (!pyWorker) return;
  try {
    await sendCommand({ action: 'close' });
  } catch (e) {
    console.error('[closeWorker] sendCommand error:', e);
  } finally {
    try {
      pyWorker.kill('SIGTERM');
    } catch (e) {
      console.error('[closeWorker] kill error:', e);
    }
    pyWorker = null;
  }
}

const runLoginScript = async (req, res, next) => {
  const { email, password, otp } = req.body;
  let formFilePath;
  let pdfFilePaths;
  if (req.files?.excel?.[0]?.path) {
    formFilePath = path.join(process.cwd(), req.files.excel[0].path);
  }
  if (req.files?.pdfs?.length) {
    pdfFilePaths = req.files.pdfs.map(file => file.path);
  }
  
  try {
    let payload;

    if (otp) {
      payload = { action: "otp", otp };
    } else if (formFilePath) {
      payload = { action: "formFill", file: formFilePath, pdfs: pdfFilePaths };
    } else {
      payload = { action: "login", email, password };
    }

    const result = await sendCommand(payload);
    res.json(result);
  } catch (err) {
    console.error("[runLoginScript] error:", err);
    next(err instanceof AppError ? err : new AppError(String(err), 500));
  }
};

module.exports = {
  runPythonScript,
  runLoginScript,
  closeWorker,
};
