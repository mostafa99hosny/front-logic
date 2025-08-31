require('dotenv').config();

const express = require('express');
const cors = require('cors');
const corsOptions = require('./shared/configs/cors.config');
const indexRoutes = require('./presentation/routes/index.routes');

const app = express();

app.use(cors(corsOptions));
app.use(express.json());

app.use(indexRoutes);

app.use((req, res) => res.status(404).json({ message: 'Not found' }));

module.exports = app;