const express = require('express');
const multer = require('multer');
const path = require('path');
const {
  createTicket,
  getAllTickets,
  getTicketById,
  downloadAttachment
} = require('../controllers/ticket.controller');
const authMiddleware = require('../../shared/middlewares/auth.middleware');

const router = express.Router();

// Configure multer for file uploads
const storage = multer.diskStorage({
  destination: function (req, file, cb) {
    cb(null, 'uploads/'); // Make sure this folder exists
  },
  filename: function (req, file, cb) {
    const uniqueSuffix = Date.now() + '-' + Math.round(Math.random() * 1E9);
    cb(null, uniqueSuffix + path.extname(file.originalname));
  }
});

const upload = multer({
  storage: storage,
  limits: {
    fileSize: 10 * 1024 * 1024 // 10MB limit
  },
  fileFilter: (req, file, cb) => {
    const allowedTypes = /jpeg|jpg|png|pdf/;
    const extname = allowedTypes.test(path.extname(file.originalname).toLowerCase());
    const mimetype = allowedTypes.test(file.mimetype);

    if (mimetype && extname) {
      return cb(null, true);
    } else {
      cb(new Error('Only JPG, PNG and PDF files are allowed'));
    }
  }
});

// Routes
router.post('/create', authMiddleware, upload.array('attachments', 5), createTicket);
router.get('/', authMiddleware, getAllTickets);
router.get('/:id', authMiddleware, getTicketById);

// Download attachment
router.get('/:ticketId/attachments/:filename', downloadAttachment);

module.exports = router;
