// front-logic/src/presentation/routes/report.routes.js
const express = require('express');
const router = express.Router();

// Assuming you have a Report model or service
const Report = require('../../infrastructure/models/report.model'); // You'll need to create this

// GET /api/reports - Fetch all reports with optional filtering
router.get('/', async (req, res) => {
  try {
    const {
      reportName,
      site,
      propertyType,
      condition,
      fromDate,
      toDate,
      page = 1,
      limit = 25
    } = req.query;

    // Build filter object
    const filter = {};
    
    if (reportName) {
      filter.reportName = { $regex: reportName, $options: 'i' };
    }
    
    if (site) {
      filter.site = site;
    }
    
    if (propertyType) {
      filter.propertyType = propertyType;
    }
    
    if (condition) {
      filter.condition = condition;
    }
    
    // Date range filter
    if (fromDate || toDate) {
      filter.date = {};
      if (fromDate) {
        filter.date.$gte = new Date(fromDate);
      }
      if (toDate) {
        filter.date.$lte = new Date(toDate);
      }
    }

    // Calculate pagination
    const skip = (page - 1) * limit;
    
    // Fetch reports with pagination
    const reports = await Report.find(filter)
      .sort({ date: -1 }) // Sort by date descending
      .skip(skip)
      .limit(parseInt(limit));
    
    // Get total count for pagination
    const totalReports = await Report.countDocuments(filter);
    
    res.json({
      success: true,
      data: {
        reports,
        pagination: {
          currentPage: parseInt(page),
          totalPages: Math.ceil(totalReports / limit),
          totalReports,
          hasNext: page * limit < totalReports,
          hasPrev: page > 1
        }
      }
    });
    
  } catch (error) {
    console.error('Error fetching reports:', error);
    res.status(500).json({
      success: false,
      message: 'Failed to fetch reports',
      error: error.message
    });
  }
});

// GET /api/reports/:id - Fetch specific report by ID
router.get('/:id', async (req, res) => {
  try {
    const { id } = req.params;
    
    const report = await Report.findById(id);
    
    if (!report) {
      return res.status(404).json({
        success: false,
        message: 'Report not found'
      });
    }
    
    res.json({
      success: true,
      data: report
    });
    
  } catch (error) {
    console.error('Error fetching report:', error);
    res.status(500).json({
      success: false,
      message: 'Failed to fetch report',
      error: error.message
    });
  }
});

module.exports = router;