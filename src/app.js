require('dotenv').config();

const express = require('express');
const cors = require('cors');
const path = require('path');
const fs = require('fs');
const corsOptions = require('./shared/configs/cors.config');
const indexRoutes = require('./presentation/routes/index.routes');

const app = express();

// Create uploads directory if it doesn't exist
const uploadsDir = path.join(__dirname, 'uploads');
if (!fs.existsSync(uploadsDir)) {
  fs.mkdirSync(uploadsDir, { recursive: true });
  console.log('Upload directory created:', uploadsDir);
}

app.use(cors(corsOptions));
app.use(express.json());
app.use(express.urlencoded({ extended: true }));

// Serve uploaded files
app.use('/uploads', express.static(uploadsDir));

app.use(indexRoutes);

app.use((req, res) => res.status(404).json({ message: 'Not found' }));

module.exports = app;