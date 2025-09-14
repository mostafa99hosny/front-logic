const express = require('express');
const upload = require('../../shared/middlewares/upload');

const { runTaqeemScript, retryTaqeemScript } = require('../controllers/script.controller');
const { runMeqyasScript, runMultipleMeqyasScript } = require('../controllers/meqyas.controller');
const { loginOrOtp, fillHalfReportForm, addAssetsToReport } = require('../controllers/halfReport.controller'); 

const scriptRouter = express.Router();

scriptRouter.post(
  '/taqeemLogin',
  upload.fields([
    { name: 'excel', maxCount: 1 },
    { name: 'pdfs', maxCount: 10 }
  ]),
  runTaqeemScript
);

scriptRouter.post('/retryTaqeem/:batchId', retryTaqeemScript);

scriptRouter.post('/meqyas', runMeqyasScript);
scriptRouter.post('/meqyasMultiple', runMultipleMeqyasScript);

scriptRouter.post(
  '/equip/login',
  loginOrOtp
);

scriptRouter.post(
  '/equip/fillForm',
  upload.fields([
    { name: 'excel', maxCount: 1 },
    { name: 'pdfs', maxCount: 1 }
  ]),
  fillHalfReportForm
);

scriptRouter.post(
  '/equip/addAssets',
  upload.fields([
    { name: 'excel', maxCount: 1 },
  ]),
  addAssetsToReport
);

module.exports = scriptRouter;
