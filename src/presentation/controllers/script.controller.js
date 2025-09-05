const { spawn } = require('child_process');
const path = require('path');
const AppError = require('../../shared/utils/appError');

let pyWorker = null;
let stdoutBuffer = '';
const pending = [];

function ensurePyWorker() {
  if (pyWorker && !pyWorker.killed) return pyWorker;

  const isWin = process.platform === 'win32';

  const venvPython = isWin
    ? path.join(__dirname, '../../../.venv/Scripts/python.exe')
    : path.join(__dirname, '../../../.venv/bin/python');
    
  const scriptPath = path.join(__dirname, '../../scripts/taqeem/worker_taqeem.py');

  pyWorker = spawn(venvPython, [scriptPath], {
    cwd: path.join(__dirname, '../../scripts/taqeem'),
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
        continue;
      }

      const handlers = pending.filter(req =>
        req.handler && typeof req.handler === 'function'
      );

      if (handlers.length > 0) {
        handlers.forEach(req => {
          try {
            req.handler(parsed);
          } catch (handlerErr) {
            console.error('[PY] Handler error:', handlerErr);
          }
        });
      } else {
        console.warn('[PY] Received response with no pending handler:', parsed);
      }
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
    const responses = [];
    let isComplete = false;

    const responseHandler = (data) => {
      responses.push(data);

      const finalStatuses = [
        'FORM_FILL_SUCCESS',
        'FAILED',
        'FATAL',
        'CLOSED',
        'SUCCESS',
        'OTP_REQUIRED',
        'LOGIN_SUCCESS'
      ];

      if (finalStatuses.includes(data.status) && !isComplete) {
        isComplete = true;

        const index = pending.findIndex(req => req.handler === responseHandler);
        if (index !== -1) {
          pending.splice(index, 1);
        }

        resolve(responses);
      }
    };

    const errorHandler = (err) => {
      if (!isComplete) {
        isComplete = true;
        reject(err);
      }
    };

    pending.push({ handler: responseHandler, reject: errorHandler });

    try {
      py.stdin.write(JSON.stringify(cmdObj) + '\n');
    } catch (e) {
      const index = pending.findIndex(req => req.handler === responseHandler);
      if (index !== -1) {
        pending.splice(index, 1);
      }
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

const runTaqeemScript = async (req, res, next) => {
  const { email, password, otp } = req.body;
  let formFilePath;
  let pdfFilePaths;

  if (req.files?.excel?.[0]?.path) {
    formFilePath = req.files.excel[0].path;
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

    const responses = await sendCommand(payload);

    if (formFilePath && responses.length > 0) {
      res.json(responses[responses.length - 1]);
    } else {
      res.json(responses[0] || { status: "UNKNOWN_RESPONSE" });
    }

  } catch (err) {
    console.error("[runTaqeemScript] error:", err);
    next(err instanceof AppError ? err : new AppError(String(err), 500));
  }
};

module.exports = {
  runTaqeemScript,
  closeWorker,
};
