class ReportResponse {
  static successWithPagination(res, data) {
    return res.status(200).json({
      success: true,
      message: 'Reports retrieved successfully',
      data: {
        reports: data.reports,
        pagination: data.pagination,
        total: data.pagination.totalReports
      }
    });
  }
  static success(res, data, message = 'Operation completed successfully') {
    return res.status(200).json({
      success: true,
      message,
      data
    });
  }
  static searchSuccess(res, data, searchTerm = null) {
    return res.status(200).json({
      success: true,
      message: `Search completed${searchTerm ? ` for "${searchTerm}"` : ''}`,
      data: {
        reports: data,
        searchTerm,
        count: data.length
      }
    });
  }

  static statsSuccess(res, stats) {
    return res.status(200).json({
      success: true,
      message: 'Statistics retrieved successfully',
      data: {
        statistics: stats
      }
    });
  }

  /**
   * Success response for filter options
   */
  static filterOptionsSuccess(res, options) {
    return res.status(200).json({
      success: true,
      message: 'Filter options retrieved successfully',
      data: options
    });
  }

  /**
   * Success response for reports summary
   */
  static summarySuccess(res, summary) {
    return res.status(200).json({
      success: true,
      message: 'Reports summary retrieved successfully',
      data: summary
    });
  }

  /**
   * Success response for export data
   */
  static exportSuccess(res, data, format = 'json') {
    const timestamp = new Date().toISOString().split('T')[0];
    
    if (format === 'csv') {
      res.setHeader('Content-Type', 'text/csv; charset=utf-8');
      res.setHeader('Content-Disposition', `attachment; filename="reports_export_${timestamp}.csv"`);
      return res.send(data);
    }
    
    // JSON export
    res.setHeader('Content-Type', 'application/json; charset=utf-8');
    res.setHeader('Content-Disposition', `attachment; filename="reports_export_${timestamp}.json"`);
    
    return res.json({
      success: true,
      message: 'Export completed successfully',
      exportDate: new Date().toISOString(),
      totalRecords: Array.isArray(data) ? data.length : (data.reports ? data.reports.length : 0),
      data: data
    });
  }

  /**
   * Success response for created resources
   */
  static created(res, data, message = 'Resource created successfully') {
    return res.status(201).json({
      success: true,
      message,
      data
    });
  }

  /**
   * Success response for updated resources
   */
  static updated(res, data, message = 'Resource updated successfully') {
    return res.status(200).json({
      success: true,
      message,
      data
    });
  }

  /**
   * Success response for deleted resources
   */
  static deleted(res, message = 'Resource deleted successfully') {
    return res.status(200).json({
      success: true,
      message,
      data: null
    });
  }

  /**
   * No content response (204)
   */
  static noContent(res) {
    return res.status(204).send();
  }

  /**
   * Error response for bad request (400)
   */
  static badRequest(res, message, errors = null) {
    const response = {
      success: false,
      message: message || 'Bad request',
      error: {
        code: 'BAD_REQUEST',
        details: errors
      }
    };
    
    if (errors) {
      response.error.validation_errors = errors;
    }
    
    return res.status(400).json(response);
  }

  /**
   * Error response for unauthorized access (401)
   */
  static unauthorized(res, message = 'Unauthorized access') {
    return res.status(401).json({
      success: false,
      message,
      error: {
        code: 'UNAUTHORIZED',
        details: 'Authentication required'
      }
    });
  }

  /**
   * Error response for forbidden access (403)
   */
  static forbidden(res, message = 'Access forbidden') {
    return res.status(403).json({
      success: false,
      message,
      error: {
        code: 'FORBIDDEN',
        details: 'Insufficient permissions'
      }
    });
  }

  /**
   * Error response for not found resources (404)
   */
  static notFound(res, message = 'Resource not found') {
    return res.status(404).json({
      success: false,
      message,
      error: {
        code: 'NOT_FOUND',
        details: 'The requested resource was not found'
      }
    });
  }

  /**
   * Error response for method not allowed (405)
   */
  static methodNotAllowed(res, allowedMethods = []) {
    res.set('Allow', allowedMethods.join(', '));
    return res.status(405).json({
      success: false,
      message: 'Method not allowed',
      error: {
        code: 'METHOD_NOT_ALLOWED',
        details: `Allowed methods: ${allowedMethods.join(', ')}`
      }
    });
  }

  /**
   * Error response for conflict (409)
   */
  static conflict(res, message = 'Resource conflict') {
    return res.status(409).json({
      success: false,
      message,
      error: {
        code: 'CONFLICT',
        details: 'Resource already exists or conflicts with existing data'
      }
    });
  }

  /**
   * Error response for validation errors (422)
   */
  static validationError(res, errors, message = 'Validation failed') {
    return res.status(422).json({
      success: false,
      message,
      error: {
        code: 'VALIDATION_ERROR',
        details: 'The provided data failed validation',
        validation_errors: errors
      }
    });
  }

  /**
   * Error response for too many requests (429)
   */
  static tooManyRequests(res, message = 'Too many requests') {
    return res.status(429).json({
      success: false,
      message,
      error: {
        code: 'RATE_LIMIT_EXCEEDED',
        details: 'Rate limit exceeded. Please try again later.'
      }
    });
  }

  /**
   * Error response for server errors (500)
   */
  static serverError(res, message, error = null) {
    // Log error for debugging (don't expose sensitive info to client)
    if (error) {
      console.error(`Server Error: ${message}`, {
        error: error.message,
        stack: error.stack,
        timestamp: new Date().toISOString()
      });
    }

    return res.status(500).json({
      success: false,
      message: message || 'Internal server error',
      error: {
        code: 'INTERNAL_SERVER_ERROR',
        details: process.env.NODE_ENV === 'production' 
          ? 'An unexpected error occurred' 
          : error?.message || 'Unknown server error'
      }
    });
  }

  /**
   * Error response for service unavailable (503)
   */
  static serviceUnavailable(res, message = 'Service temporarily unavailable') {
    return res.status(503).json({
      success: false,
      message,
      error: {
        code: 'SERVICE_UNAVAILABLE',
        details: 'The service is temporarily unavailable. Please try again later.'
      }
    });
  }

  /**
   * Error response for database errors
   */
  static databaseError(res, message = 'Database error occurred') {
    return res.status(500).json({
      success: false,
      message,
      error: {
        code: 'DATABASE_ERROR',
        details: 'A database operation failed'
      }
    });
  }

  /**
   * Generic error response handler
   */
  static handleError(res, error, defaultMessage = 'An error occurred') {
    console.error('Error handled by ReportResponse:', {
      message: error.message,
      stack: error.stack,
      name: error.name,
      timestamp: new Date().toISOString()
    });

    // Handle specific error types
    if (error.name === 'ValidationError') {
      return this.validationError(res, error.errors, 'Data validation failed');
    }

    if (error.name === 'CastError') {
      return this.badRequest(res, 'Invalid data format provided');
    }

    if (error.name === 'MongoError' || error.name === 'MongoServerError') {
      return this.databaseError(res, 'Database operation failed');
    }

    if (error.code === 'ECONNREFUSED') {
      return this.serviceUnavailable(res, 'Database connection refused');
    }

    // Default to server error
    return this.serverError(res, defaultMessage, error);
  }

  /**
   * Success response with custom status code
   */
  static customSuccess(res, statusCode, data, message) {
    return res.status(statusCode).json({
      success: true,
      message,
      data
    });
  }

  /**
   * Error response with custom status code
   */
  static customError(res, statusCode, message, errorCode = null) {
    return res.status(statusCode).json({
      success: false,
      message,
      error: {
        code: errorCode || `HTTP_${statusCode}`,
        details: message
      }
    });
  }
}

module.exports = ReportResponse;