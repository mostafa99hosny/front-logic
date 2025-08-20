// src/routes/users.routes.js
const express = require('express');
const router = express.Router();

// Temporary placeholder route (no controller yet)
router.get('/', (req, res) => {
  res.json({ message: 'User route works' });
});

module.exports = router;
