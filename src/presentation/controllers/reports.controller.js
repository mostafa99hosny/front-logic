// front-logic/src/presentation/controllers/reports.controller.js
const ReportService = require('../../application/reports/report.service');
const ReportResponse = require('../../application/reports/report.response');

class ReportController {
  /**
   * GET /api/reports - Fetch all reports with optional filtering
   */
  static async getAllReports(req, res) {
    try {
      const result = await ReportService.getReports(req.query);
      return ReportResponse.successWithPagination(res, result);
    } catch (error) {
      return ReportResponse.handleError(res, error, 'Failed to fetch reports');
    }
  }

  /**
   * GET /api/reports/:id - Fetch specific report by ID
   */
  static async getReportById(req, res) {
    try {
      const { id } = req.params;
      
      // Validate MongoDB ObjectId format
      if (!id.match(/^[0-9a-fA-F]{24}$/)) {
        return ReportResponse.badRequest(res, 'Invalid report ID format');
      }
      
      const report = await ReportService.getReportById(id);
      
      if (!report) {
        return ReportResponse.notFound(res, 'Report not found');
      }
      
      return ReportResponse.success(res, report, 'Report retrieved successfully');
    } catch (error) {
      return ReportResponse.handleError(res, error, 'Failed to fetch report');
    }
  }

  /**
   * GET /api/reports/stats - Get report statistics
   */
  static async getReportStats(req, res) {
    try {
      const stats = await ReportService.getReportStats();
      return ReportResponse.statsSuccess(res, stats);
    } catch (error) {
      return ReportResponse.handleError(res, error, 'Failed to fetch report statistics');
    }
  }

  /**
   * POST /api/reports/search - Advanced search reports
   */
  static async searchReports(req, res) {
    try {
      const { searchTerm, filters = {} } = req.body;
      
      if (!searchTerm || searchTerm.trim().length < 2) {
        return ReportResponse.badRequest(res, 'Search term must be at least 2 characters long');
      }
      
      const reports = await ReportService.searchReports(searchTerm.trim(), filters);
      return ReportResponse.searchSuccess(res, reports, searchTerm);
    } catch (error) {
      return ReportResponse.handleError(res, error, 'Failed to search reports');
    }
  }

  /**
   * GET /api/reports/filter-options - Get filter dropdown options
   */
  static async getFilterOptions(req, res) {
    try {
      const options = await ReportService.getFilterOptions();
      return ReportResponse.filterOptionsSuccess(res, options);
    } catch (error) {
      return ReportResponse.handleError(res, error, 'Failed to fetch filter options');
    }
  }

  /**
   * GET /api/reports/export - Export reports data
   */
  static async exportReports(req, res) {
    try {
      const { format = 'json', ...filters } = req.query;
      
      // Remove pagination for export - get all matching records
      const exportFilters = { ...filters, limit: 10000, page: 1 };
      
      const result = await ReportService.getReports(exportFilters);
      
      if (format === 'csv') {
        const csvData = ReportService.convertToCSV(result.reports);
        return ReportResponse.exportSuccess(res, csvData, 'csv');
      }
      
      // Default JSON export
      return ReportResponse.exportSuccess(res, result, 'json');
      
    } catch (error) {
      return ReportResponse.handleError(res, error, 'Failed to export reports');
    }
  }

  /**
   * GET /api/reports/summary - Get reports summary by groupings
   */
  static async getReportsSummary(req, res) {
    try {
      const { groupBy = 'propertyType' } = req.query;
      
      const summary = await ReportService.getReportsSummary(groupBy);
      return ReportResponse.summarySuccess(res, summary);
      
    } catch (error) {
      return ReportResponse.handleError(res, error, 'Failed to fetch reports summary');
    }
  }

  /**
   * POST /api/reports - Create new report (if needed)
   */
  static async createReport(req, res) {
    try {
      // Implementation depends on your requirements
      // This is just a placeholder structure
      const reportData = req.body;
      
      // Validate required fields
      if (!reportData.query || !reportData.payload) {
        return ReportResponse.badRequest(res, 'Query and payload are required');
      }

      // You would implement the creation logic here
      // const newReport = await ReportService.createReport(reportData);
      
      return ReportResponse.created(res, null, 'Report creation endpoint - implementation needed');
    } catch (error) {
      return ReportResponse.handleError(res, error, 'Failed to create report');
    }
  }

  /**
   * PUT /api/reports/:id - Update existing report (if needed)
   */
  static async updateReport(req, res) {
    try {
      const { id } = req.params;
      const updateData = req.body;
      
      // Validate MongoDB ObjectId format
      if (!id.match(/^[0-9a-fA-F]{24}$/)) {
        return ReportResponse.badRequest(res, 'Invalid report ID format');
      }

      // You would implement the update logic here
      // const updatedReport = await ReportService.updateReport(id, updateData);
      
      return ReportResponse.updated(res, null, 'Report update endpoint - implementation needed');
    } catch (error) {
      return ReportResponse.handleError(res, error, 'Failed to update report');
    }
  }

  /**
   * DELETE /api/reports/:id - Delete report (if needed)
   */
  static async deleteReport(req, res) {
    try {
      const { id } = req.params;
      
      // Validate MongoDB ObjectId format
      if (!id.match(/^[0-9a-fA-F]{24}$/)) {
        return ReportResponse.badRequest(res, 'Invalid report ID format');
      }

      // You would implement the deletion logic here
      // await ReportService.deleteReport(id);
      
      return ReportResponse.deleted(res, 'Report deletion endpoint - implementation needed');
    } catch (error) {
      return ReportResponse.handleError(res, error, 'Failed to delete report');
    }
  }

  /**
   * GET /api/reports/bulk/ids - Get multiple reports by IDs
   */
  static async getReportsByIds(req, res) {
    try {
      const { ids } = req.query;
      
      if (!ids) {
        return ReportResponse.badRequest(res, 'Report IDs are required');
      }

      const reportIds = Array.isArray(ids) ? ids : ids.split(',');
      
      // Validate all IDs are valid MongoDB ObjectIds
      const invalidIds = reportIds.filter(id => !id.match(/^[0-9a-fA-F]{24}$/));
      if (invalidIds.length > 0) {
        return ReportResponse.badRequest(res, `Invalid ID format: ${invalidIds.join(', ')}`);
      }

      // You would implement the bulk fetch logic here
      // const reports = await ReportService.getReportsByIds(reportIds);
      
      return ReportResponse.success(res, [], 'Bulk fetch endpoint - implementation needed');
    } catch (error) {
      return ReportResponse.handleError(res, error, 'Failed to fetch reports by IDs');
    }
  }

  /**
   * POST /api/reports/validate - Validate report data
   */
  static async validateReport(req, res) {
    try {
      const reportData = req.body;
      
      // Basic validation
      const errors = [];
      
      if (!reportData.type || reportData.type !== 'eval_model_scraped') {
        errors.push('Invalid or missing report type');
      }
      
      if (!reportData.query || typeof reportData.query !== 'string') {
        errors.push('Query field is required and must be a string');
      }
      
      if (!reportData.payload || typeof reportData.payload !== 'object') {
        errors.push('Payload field is required and must be an object');
      }
      
      if (errors.length > 0) {
        return ReportResponse.validationError(res, errors);
      }
      
      return ReportResponse.success(res, { valid: true }, 'Report data is valid');
    } catch (error) {
      return ReportResponse.handleError(res, error, 'Failed to validate report');
    }
  }

  /**
   * GET /api/reports/health - Health check endpoint
   */
  static async healthCheck(req, res) {
    try {
      // Basic health check - verify database connection
      const stats = await ReportService.getReportStats();
      
      return ReportResponse.success(res, {
        status: 'healthy',
        timestamp: new Date().toISOString(),
        totalReports: stats.totalReports,
        database: 'connected'
      }, 'Service is healthy');
    } catch (error) {
      return ReportResponse.serviceUnavailable(res, 'Service health check failed');
    }
  }
}

module.exports = ReportController;