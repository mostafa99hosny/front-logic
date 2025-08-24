const { spawn } = require('child_process');
const path = require('path');

const runPythonScript = (req, res) => {
  if (!req.files?.excel?.[0] || !req.files?.pdfs?.length) {
    return res
      .status(400)
      .json({ message: 'Upload both Excel and at least one PDF file.' });
  }

  const excelPath = req.files.excel[0].path;
  const pdfPaths = req.files.pdfs.map(f => f.path);

  const scriptPath = path.join(__dirname, '../../scripts/dummy.py');
  const venvPython = path.join(__dirname, '../../../.venv/bin/python');

  const args = [scriptPath, excelPath, ...pdfPaths];
  const py = spawn(venvPython, args);

  let output = '';
  py.stdout.on('data', data => (output += data.toString()));
  py.stderr.on('data', data => console.error(`Python error: ${data}`));
  py.on('close', code => {
    console.log(`Python script exited with code ${code}`);
    res.json({ success: code === 0, output });
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

  pyWorker.on('spawn', () => {
    console.log('[PY] Worker spawned');
  });

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
        if (req) req.reject(new Error('Invalid JSON from Python'));
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
      req.reject(new Error('Python worker exited'));
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
      return reject(e);
    }
  });
}

async function closeWorker() {
  if (!pyWorker) return;
  try {
    await sendCommand({ action: 'close' });
  } catch (e) {
  } finally {
    try {
      pyWorker.kill('SIGTERM');
    } catch (e) {}
    pyWorker = null;
  }
}

const runLoginScript = async (req, res) => {
  const { email, password, otp } = req.body;
  console.log("data:", email, password, otp);

  if (!email || !password) {
    return res.status(400).json({ message: 'Email and password are required.' });
  }

  try {
    const payload = otp
      ? { action: 'otp', otp }
      : { action: 'login', email, password };

    const result = await sendCommand(payload);
    return res.json(result);
  } catch (err) {
    console.error('[runLoginScript] error:', err);
    return res.status(500).json({ status: 'FAILED', error: String(err) });
  }
};

module.exports = {
  runPythonScript,
  runLoginScript,
  closeWorker,
};
