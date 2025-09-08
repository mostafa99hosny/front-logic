const express = require('express');
const upload = require('../../shared/middlewares/upload');

const { runTaqeemScript, retryTaqeemScript } = require('../controllers/script.controller');
const { runMeqyasScript, runMultipleMeqyasScript } = require('../controllers/meqyas.controller');

const scriptRouter = express.Router();

scriptRouter.post(
  '/taqeemLogin', upload.fields([
    { name: 'excel', maxCount: 1 }, 
    { name: 'pdfs', maxCount: 10 }  
  ]),
  runTaqeemScript
);

scriptRouter.post('/retryTaqeem/:batchId', retryTaqeemScript);
scriptRouter.post('/meqyas', runMeqyasScript);
scriptRouter.post('/meqyasMultiple', runMultipleMeqyasScript);

module.exports = scriptRouter;
