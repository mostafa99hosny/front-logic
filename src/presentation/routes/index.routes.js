// src/routes/index.routes.js
const express = require('express');
const mongoose = require('mongoose');

const router = express.Router();

router.get('/', (_req, res) => {
  res.json({ message: 'Welcome to front-logic API' });
});

router.get('/health', (_req, res) => {
  const states = ['disconnected', 'connected', 'connecting', 'disconnecting', 'uninitialized'];
  const state = states[mongoose.connection.readyState] || 'unknown';
  res.json({ status: 'ok', dbState: state });
});

module.exports = router;   
