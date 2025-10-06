const express = require('express');
const { sendMessage, getMessages } = require('../controllers/message.controller');
const authMiddleware = require('../../shared/middlewares/auth.middleware');

const router = express.Router();

// Get messages for a ticket
router.get('/:ticketId', authMiddleware, getMessages);

// Send a message to a ticket
router.post('/:ticketId', authMiddleware, sendMessage);

module.exports = router;