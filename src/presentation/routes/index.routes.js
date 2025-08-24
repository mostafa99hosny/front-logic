const userRoutes = require('./users.routes')
const express = require('express');
const mongoose = require('mongoose');

const paymentRouter = require('./payment.routes');

const router = express.Router();
router.use('/api/users', userRoutes);
router.use('/api/payments', paymentRouter);

router.get('/', (_req, res) => {
  res.json({ message: 'Welcome to front-logic API' });
});

router.get('/health', (_req, res) => {
  const states = ['disconnected', 'connected', 'connecting', 'disconnecting', 'uninitialized'];
  const state = states[mongoose.connection.readyState] || 'unknown';
  res.json({ status: 'ok', dbState: state });
});

module.exports = router;   
