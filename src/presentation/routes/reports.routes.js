// front-logic/src/presentation/routes/reports.routes.js
const express = require('express');
const router = express.Router();
const ReportController = require('../controllers/reports.controller');

// GET /api/reports/health - Health check endpoint
router.get('/health', ReportController.healthCheck);

// GET /api/reports/stats - Get report statistics (must be before /:id route)
router.get('/stats', ReportController.getReportStats);

// GET /api/reports/filter-options - Get filter dropdown options
router.get('/filter-options', ReportController.getFilterOptions);

router.post('/createHalfReport', ReportController.createHalfReport);

// GET /api/reports/export - Export reports data
router.get('/export', ReportController.exportReports);

// GET /api/reports/summary - Get reports summary by groupings
router.get('/summary', ReportController.getReportsSummary);

// GET /api/reports/bulk/ids - Get multiple reports by IDs
router.get('/bulk/ids', ReportController.getReportsByIds);

// GET /api/reports - Fetch all reports with optional filtering
router.get('/', ReportController.getAllReports);

// GET /api/reports/:id - Fetch specific report by ID
router.get('/:id', ReportController.getReportById);

// POST /api/reports/search - Advanced search reports
router.post('/search', ReportController.searchReports);

// POST /api/reports/validate - Validate report data
router.post('/validate', ReportController.validateReport);

// POST /api/reports - Create new report (if needed)
router.post('/', ReportController.createReport);

// PUT /api/reports/:id - Update existing report (if needed)
router.put('/:id', ReportController.updateReport);

// DELETE /api/reports/:id - Delete report (if needed)
router.delete('/:id', ReportController.deleteReport);

module.exports = router;