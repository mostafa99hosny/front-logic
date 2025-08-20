const mongoose = require('mongoose');

let isConnected = false;

async function connectDB(uri) {
  if (isConnected) return mongoose.connection;

  mongoose.connection.on('connected', () => {
    isConnected = true;
    console.log('✅ MongoDB connected');
  });

  mongoose.connection.on('error', (err) => {
    console.error('❌ MongoDB connection error:', err);
  });

  mongoose.connection.on('disconnected', () => {
    isConnected = false;
    console.log('⚠️ MongoDB disconnected');
  });

  await mongoose.connect(uri, {
    // Mongoose 6+ doesn’t need extra options
    // keepAlive helps long-lived serverless
    serverSelectionTimeoutMS: 15000,
    socketTimeoutMS: 45000,
  });

  return mongoose.connection;
}

module.exports = { connectDB };
