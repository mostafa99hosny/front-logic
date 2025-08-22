const express = require('express');
const upload = require('../../shared/middlewares/upload');

const { runPythonScript, runLoginScript } = require('../controllers/script.controller');

const scriptRouter = express.Router();


scriptRouter.post(
    '/run',
    upload.fields([
        { name: 'excel', maxCount: 1 },
        { name: 'pdfs', maxCount: 10 },
    ]),
    runPythonScript
);

scriptRouter.post('/taqeemLogin', runLoginScript);

module.exports = scriptRouter;
