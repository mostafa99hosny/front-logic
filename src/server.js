const dotenv = require('dotenv');
dotenv.config();
const mongoose = require('mongoose');
const app = require('./app');
const http = require('http');
const { Server } = require('socket.io');
const { setSocketIO, sendCommand, activeTasks } = require('./presentation/controllers/halfReport.controller');
const Company = require('./infrastructure/models/company.model');

const PORT = process.env.PORT || 3000;
const server = http.createServer(app);
const io = new Server(server, {
  cors: {
    origin: "*", 
    methods: ["GET", "POST"]
  }
});

setSocketIO(io);

const activeSessions = new Map(); 

io.on('connection', (socket) => {
  console.log('User connected:', socket.id);

  socket.on('join_ticket', (ticketId) => {
    socket.join(ticketId);
    console.log(`User ${socket.id} joined ticket ${ticketId}`);
  });

  socket.on('join_tickets', (ticketIds) => {
    ticketIds.forEach(ticketId => {
      socket.join(ticketId);
    });
    console.log(`User ${socket.id} joined tickets: ${ticketIds.join(', ')}`);
  });

  socket.on('send_message', (data) => {
    console.log('send_message received:', data);
    io.to(data.ticketId).emit('receive_message', { 
      ...data.message, 
      ticketId: data.ticketId 
    });
    console.log('Emitted receive_message to room:', data.ticketId);
  });

  socket.on('start_form_fill', async (data) => {
    const { reportId, tabsNum, actionType = 'submit' } = data;
    console.log(`[SOCKET] start_form_fill: reportId=${reportId}, tabsNum=${tabsNum}, action=${actionType}`);

    try {
      socket.join(`report_${reportId}`);

      const controlState = {
        paused: false,
        stopped: false,
        reportId,
        actionType
      };

      activeSessions.set(reportId, {
        socket,
        controlState,
        startedAt: new Date(),
        actionType
      });

      socket.emit('form_fill_started', { 
        reportId, 
        status: 'STARTED',
        actionType 
      });

      let response;
      
      switch (actionType) {
        case 'submit':
          response = await sendCommand({ 
            action: "formFill2", 
            reportId, 
            tabsNum: tabsNum || 3,
            socketMode: true 
          });
          break;
          
        case 'retry':
          response = await sendCommand({ 
            action: "retryMacros", 
            recordId: reportId, 
            tabsNum: tabsNum || 3,
            socketMode: true 
          });
          break;
          
        case 'check':
          response = await sendCommand({ 
            action: "checkMacros", 
            reportId, 
            tabsNum: tabsNum || 3,
            socketMode: true 
          });
          break;
          
        default:
          throw new Error(`Unknown action type: ${actionType}`);
      }

      console.log(`[SOCKET] ${actionType} response:`, response);

      if (response.status === 'SUCCESS') {
        io.to(`report_${reportId}`).emit('form_fill_complete', {
          reportId,
          status: 'SUCCESS',
          actionType,
          results: response.results || response.result,
          message: `${actionType} completed successfully`,
          timestamp: new Date().toISOString()
        });
      } else {
        io.to(`report_${reportId}`).emit('form_fill_error', {
          reportId,
          status: 'FAILED',
          actionType,
          error: response.error || 'Unknown error',
          timestamp: new Date().toISOString()
        });
      }

      activeSessions.delete(reportId);

    } catch (error) {
      console.error(`[SOCKET ERROR] start_form_fill:`, error);
      socket.emit('form_fill_error', {
        reportId,
        status: 'FAILED',
        actionType,
        error: error.message
      });
      activeSessions.delete(reportId);
    }
  });

  socket.on('pause_form_fill', async (data) => {
    const { reportId } = data;
    console.log(`[SOCKET] pause_form_fill: reportId=${reportId}`);

    const session = activeSessions.get(reportId);
    if (session) {
      try {
        const taskId = activeTasks.get(reportId);
        
        const response = await sendCommand({ 
          action: "pause", 
          reportId,
          taskId 
        }, "control");

        session.controlState.paused = true;
        socket.emit('form_fill_paused', { 
          reportId, 
          status: 'PAUSED',
          actionType: session.actionType 
        });
      } catch (error) {
        console.error(`[SOCKET ERROR] pause_form_fill:`, error);
        socket.emit('form_fill_error', {
          reportId,
          status: 'FAILED',
          error: error.message
        });
      }
    } else {
      socket.emit('form_fill_error', {
        reportId,
        status: 'FAILED',
        error: 'No active session found'
      });
    }
  });

  socket.on('resume_form_fill', async (data) => {
    const { reportId } = data;
    console.log(`[SOCKET] resume_form_fill: reportId=${reportId}`);

    const session = activeSessions.get(reportId);
    if (session) {
      try {
        const taskId = activeTasks.get(reportId);
        
        const response = await sendCommand({ 
          action: "resume", 
          reportId,
          taskId 
        }, "control");

        session.controlState.paused = false;
        socket.emit('form_fill_resumed', { 
          reportId, 
          status: 'RESUMED',
          actionType: session.actionType 
        });
      } catch (error) {
        console.error(`[SOCKET ERROR] resume_form_fill:`, error);
        socket.emit('form_fill_error', {
          reportId,
          status: 'FAILED',
          error: error.message
        });
      }
    } else {
      socket.emit('form_fill_error', {
        reportId,
        status: 'FAILED',
        error: 'No active session found'
      });
    }
  });

  socket.on('stop_form_fill', async (data) => {
    const { reportId } = data;
    console.log(`[SOCKET] stop_form_fill: reportId=${reportId}`);

    const session = activeSessions.get(reportId);
    if (session) {
      try {
        const taskId = activeTasks.get(reportId);
        
        const response = await sendCommand({ 
          action: "stop", 
          reportId,
          taskId 
        }, "control");

        session.controlState.stopped = true;
        socket.emit('form_fill_stopped', { 
          reportId, 
          status: 'STOPPED',
          actionType: session.actionType 
        });
        activeSessions.delete(reportId);
      } catch (error) {
        console.error(`[SOCKET ERROR] stop_form_fill:`, error);
        socket.emit('form_fill_error', {
          reportId,
          status: 'FAILED',
          error: error.message
        });
      }
    } else {
      socket.emit('form_fill_error', {
        reportId,
        status: 'FAILED',
        error: 'No active session found'
      });
    }
  });

  socket.on('get_active_sessions', () => {
    const sessions = Array.from(activeSessions.entries()).map(([reportId, session]) => ({
      reportId,
      startedAt: session.startedAt,
      paused: session.controlState.paused,
      stopped: session.controlState.stopped,
      actionType: session.actionType
    }));
    socket.emit('active_sessions', sessions);
  });

  socket.on('disconnect', () => {
    console.log('User disconnected:', socket.id);
    
    for (const [reportId, session] of activeSessions.entries()) {
      if (session.socket.id === socket.id) {
        console.log(`[CLEANUP] Removing session for reportId=${reportId}`);
        activeSessions.delete(reportId);
      }
    }
  });
});

mongoose.connect(process.env.MONGO_URI)
  .then(async () => {
    console.log('✅ MongoDB connected');

    // Ensure no legacy unique index on secretKey exists
    try {
      const indexes = await Company.collection.indexes();
      const hasSecretKeyIndex = indexes.some(idx => idx.name === 'secretKey_1');
      if (hasSecretKeyIndex) {
        await Company.collection.dropIndex('secretKey_1');
        console.log('🛠️ Dropped legacy index secretKey_1 from companies collection');
      }
    } catch (indexErr) {
      if (indexErr && indexErr.codeName !== 'IndexNotFound') {
        console.error('Index cleanup error:', indexErr);
      }
    }

    // Sync indexes to schema
    try {
      await Company.syncIndexes();
    } catch (syncErr) {
      console.error('syncIndexes error:', syncErr);
    }

    server.listen(PORT, () => {
      console.log(`🚀 Server running on http://localhost:${PORT}`);
    });
  })
  .catch((err) => {
    console.error('❌ MongoDB connection error:', err);
    process.exit(1);
  });

module.exports = { io, activeSessions };