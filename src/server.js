const dotenv = require('dotenv');
dotenv.config();

const mongoose = require('mongoose');
const app = require('./app');
const http = require('http');
const { Server } = require('socket.io');
const Ticket = require('./infrastructure/models/ticket.model');

const PORT = process.env.PORT || 3000;
const server = http.createServer(app);
const io = new Server(server, {
  cors: {
    origin: "*", // In production, specify your frontend URL
    methods: ["GET", "POST"]
  }
});

// Socket.io connection handling
io.on('connection', (socket) => {
  console.log('User connected:', socket.id);

  // Join a ticket room
  socket.on('join_ticket', (ticketId) => {
    socket.join(ticketId);
    console.log(`User ${socket.id} joined ticket ${ticketId}`);
  });

  // Join multiple ticket rooms
  socket.on('join_tickets', (ticketIds) => {
    ticketIds.forEach(ticketId => {
      socket.join(ticketId);
    });
    console.log(`User ${socket.id} joined tickets: ${ticketIds.join(', ')}`);
  });

  // Handle sending message
  socket.on('send_message', (data) => {
    console.log('send_message received:', data);
    // Emit to all users in the ticket room (message already saved by API)
    io.to(data.ticketId).emit('receive_message', { ...data.message, ticketId: data.ticketId });
    console.log('Emitted receive_message to room:', data.ticketId);
  });

  socket.on('disconnect', () => {
    console.log('User disconnected:', socket.id);
  });
});

mongoose.connect(process.env.MONGO_URI)
  .then(() => {
    console.log('✅ MongoDB connected');
    server.listen(PORT, () => {
      console.log(`🚀 Server running on http://localhost:${PORT}`);
    });
  })
  .catch((err) => {
    console.error('❌ MongoDB connection error:', err);
    process.exit(1);
  });
