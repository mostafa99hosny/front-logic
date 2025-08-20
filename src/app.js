const express = require('express');
const cors = require('cors');
const corsOptions = require('./shared/configs/cors.config');
const indexRoutes = require('./presentation/routes/index.routes');
const userRoutes = require('./presentation/routes/users.routes');

const app = express();

app.use(cors(corsOptions));
app.use(express.json());

// Health & base routes
app.use('/', indexRoutes);
app.use('/api/users', userRoutes);

// 404
app.use((req, res) => res.status(404).json({ message: 'Not found' }));

module.exports = app;
