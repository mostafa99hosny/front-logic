const { spawn } = require('child_process');
const path = require('path');
const AppError = require('../../shared/utils/appError');

const runMeqyasScript = async (req, res, next) => {
    const { username, password, query } = req.body;

    if (!username || !password || !query) {
        return next(new AppError('username, password, and query are required', 400));
    }

    const isWin = process.platform === 'win32';

    const venvPython = isWin
        ? path.join(__dirname, '../../../.venv/Scripts/python.exe')
        : path.join(__dirname, '../../../.venv/bin/python');
        
    const scriptCwd = path.join(__dirname, '../../scripts/meqyas');

    const py = spawn(venvPython, ["-m", "src.main", username, password, query], {
        cwd: scriptCwd,
    });

    let stdout = '';
    let stderr = '';

    py.stdout.on('data', (data) => {
        stdout += data.toString();
    });

    py.stderr.on('data', (data) => {
        stderr += data.toString();
        console.error(`[PY STDERR eval] ${data.toString()}`);
    });

    py.on('close', (code) => {
        if (code !== 0) {
            return next(
                new AppError(
                    `Eval script failed (code ${code}): ${stderr || 'unknown error'}`,
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

module.exports = {
    runMeqyasScript,
};
