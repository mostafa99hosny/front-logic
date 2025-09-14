const { spawn } = require('child_process');
const path = require('path');
const AppError = require('../../shared/utils/appError');

const isWin = process.platform === 'win32';
const venvPython = isWin
    ? path.join(__dirname, '../../../.venv/Scripts/python.exe')
    : path.join(__dirname, '../../../.venv/bin/python');

const runPythonScript = (scriptDir, args, next, res) => {
    const py = spawn(venvPython, ["-m", "src.main", ...args], {
        cwd: scriptDir,
    });

    let stdout = '';
    let stderr = '';

    py.stdout.on('data', (data) => {
        stdout += data.toString();
    });

    py.stderr.on('data', (data) => {
        stderr += data.toString();
        console.error(`[PY STDERR] ${data.toString()}`);
    });

    py.on('close', (code) => {
        if (code !== 0) {
            return next(
                new AppError(
                    `Python script failed (code ${code}): ${stderr || 'unknown error'}`,
                    500
                )
            );
        }

        res.json({
            status: 'SUCCESS',
            output: stdout.trim(),
        });
    });
};

const runMeqyasScript = async (req, res, next) => {
    const { username, password, query } = req.body;

    if (!username || !password || !query) {
        return next(new AppError('username, password, and query are required', 400));
    }

    const scriptCwd = path.join(__dirname, '../../scripts/meqyas');
    runPythonScript(scriptCwd, [username, password, query], next, res);
    
    

};

const runMultipleMeqyasScript = async (req, res, next) => {
    const { username, password } = req.body;

    if (!username || !password) {
        return next(new AppError('username and password are required', 400));
    }

    const scriptCwd = path.join(__dirname, '../../scripts/meqyasMultiple');
    runPythonScript(scriptCwd, [username, password], next, res);
};

module.exports = {
    runMeqyasScript,
    runMultipleMeqyasScript,
};
