const { sendCommand } = require('./halfReport.controller');

async function handleFormFill2Socket(io, reportId, tabsNum = 3, controlState) {
  try {
    console.log(`[SOCKET CONTROLLER] Starting form fill for reportId=${reportId}`);
    
    // Send initial status
    io.to(`report_${reportId}`).emit('form_fill_progress', {
      reportId,
      status: 'INITIALIZING',
      message: 'Starting form filling process...',
      timestamp: new Date().toISOString()
    });

    // Send command to Python worker
    const payload = { 
      action: "formFill2", 
      reportId, 
      tabsNum,
      socketMode: true  // Flag to enable socket progress updates
    };

    // Create a promise that resolves when we get the final status
    const result = await new Promise((resolve, reject) => {
      // Set up a listener for Python worker stdout
      const originalSendCommand = sendCommand;
      
      // Send the command
      sendCommand(payload)
        .then(finalResult => {
          resolve(finalResult);
        })
        .catch(err => {
          reject(err);
        });
    });

    // Emit final result
    if (result.status === 'SUCCESS') {
      io.to(`report_${reportId}`).emit('form_fill_complete', {
        reportId,
        status: 'SUCCESS',
        message: 'Form filling completed successfully',
        results: result.results,
        timestamp: new Date().toISOString()
      });
    } else {
      io.to(`report_${reportId}`).emit('form_fill_error', {
        reportId,
        status: 'FAILED',
        error: result.error || 'Unknown error',
        timestamp: new Date().toISOString()
      });
    }

    return result;

  } catch (error) {
    console.error(`[SOCKET CONTROLLER ERROR] ${error.message}`);
    io.to(`report_${reportId}`).emit('form_fill_error', {
      reportId,
      status: 'FAILED',
      error: error.message,
      timestamp: new Date().toISOString()
    });
    throw error;
  }
}

/**
 * Handle pause command via socket
 */
function handlePauseSocket(controlState) {
  controlState.paused = true;
  console.log(`[SOCKET] Paused reportId=${controlState.reportId}`);
}

/**
 * Handle resume command via socket
 */
function handleResumeSocket(controlState) {
  controlState.paused = false;
  console.log(`[SOCKET] Resumed reportId=${controlState.reportId}`);
}

/**
 * Handle stop command via socket
 */
function handleStopSocket(controlState) {
  controlState.stopped = true;
  controlState.paused = false;  // Unpause if paused
  console.log(`[SOCKET] Stopped reportId=${controlState.reportId}`);
}

module.exports = {
  handleFormFill2Socket,
  handlePauseSocket,
  handleResumeSocket,
  handleStopSocket
};