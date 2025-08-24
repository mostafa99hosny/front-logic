const express = require('express');
const upload = require('../../shared/middlewares/upload');

const { runLoginScript } = require('../controllers/script.controller');

const scriptRouter = express.Router();

scriptRouter.post(
  '/taqeemLogin', upload.fields([
    { name: 'excel', maxCount: 1 }, 
    { name: 'pdfs', maxCount: 10 }  
  ]),
  runLoginScript
);

module.exports = scriptRouter;
