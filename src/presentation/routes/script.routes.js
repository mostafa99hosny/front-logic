const express = require('express');
const upload = require('../../shared/middlewares/upload');

const { runTaqeemScript } = require('../controllers/script.controller');
const { runMeqyasScript } = require('../controllers/meqyas.controller');

const scriptRouter = express.Router();

scriptRouter.post(
  '/taqeemLogin', upload.fields([
    { name: 'excel', maxCount: 1 }, 
    { name: 'pdfs', maxCount: 10 }  
  ]),
  runTaqeemScript
);

scriptRouter.post('/meqyas', runMeqyasScript);

module.exports = scriptRouter;
