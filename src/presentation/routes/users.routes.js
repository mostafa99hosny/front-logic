const express = require('express');
const userController = require('../controllers/user.controller');
const authMiddleware = require('../../shared/middlewares/auth.middleware');

const userRoutes = express.Router();

// Public routes
userRoutes.post('/auth/register', userController.register);
userRoutes.post('/auth/login', userController.login);

// Protected routes
userRoutes.get('/profile', authMiddleware, userController.getProfile);
userRoutes.get('/verify', authMiddleware, userController.verifyToken);

module.exports = userRoutes;