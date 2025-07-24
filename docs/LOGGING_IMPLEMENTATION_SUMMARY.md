# Application Logging Implementation Summary

## Overview
This document summarizes the comprehensive logging system implemented for the parking booking application. The system provides detailed application logs that are stored in the database and accessible through an admin interface with filtering and management capabilities.

## Components Implemented

### 1. Database Model (`src/booking/models.py`)
- **ApplicationLog Model**: Stores all application logs with the following fields:
  - `id`: Primary key
  - `timestamp`: When the log was created (timezone-aware)
  - `level`: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
  - `logger_name`: Name of the logger that created the log
  - `message`: The log message
  - `module`: File/module where log originated
  - `function`: Function where log originated
  - `line_number`: Line number where log originated
  - `user_id`: Associated user (if applicable)
  - `request_id`: Request ID for tracing (if applicable)
  - `extra_data`: JSON string for additional context

### 2. Logging Configuration (`src/booking/logging_config.py`)
- **DatabaseLogHandler**: Custom logging handler that stores logs in the database
- **setup_logging()**: Configures application-wide logging with both console and database handlers
- **get_logger()**: Helper function to get loggers with consistent naming
- **log_with_context()**: Helper function to log with additional context (user_id, request_id, extra_data)

### 3. Admin API Routes (`src/booking/routers/admin/logs.py`)
- **GET /api/admin/logs**: Retrieve logs with filtering options:
  - Pagination (skip, limit)
  - Filter by log level
  - Filter by logger name
  - Filter by time range (start_time, end_time)
  - Search in log messages
  - Filter by user ID
- **GET /api/admin/logs/levels**: Get all available log levels
- **GET /api/admin/logs/loggers**: Get all available logger names
- **GET /api/admin/logs/stats**: Get log statistics for specified time period
- **DELETE /api/admin/logs/cleanup**: Delete logs older than specified days

### 4. Pydantic Schemas (`src/booking/schemas.py`)
- **ApplicationLogBase**: Base schema for log data
- **ApplicationLog**: Complete log schema with relationships

### 5. Admin Interface (`templates/index.html`)
- **New "Application Logs" Tab**: Added to the admin interface with:
  - **Log Filters**: Filter by level, logger, time range, search text, user ID
  - **Log Statistics**: Shows total logs, error count, and top active loggers for last 24 hours
  - **Log Management**: Cleanup old logs functionality
  - **Logs Table**: Displays logs with pagination and detailed view
  - **Log Details Modal**: Shows complete log information including stack traces

### 6. Comprehensive Logging Integration
Added logging throughout the application:

#### Authentication & Security (`src/booking/security.py`, `src/booking/routers/users.py`)
- User login attempts (successful and failed)
- JWT token validation
- Admin access attempts
- User creation

#### Booking Operations (`src/booking/routers/bookings.py`, `src/booking/services.py`)
- Booking creation attempts
- Booking conflicts and validation errors
- Successful booking completions
- Email confirmation sending

#### Application Lifecycle (`src/booking/__init__.py`)
- Application startup and shutdown
- OIDC authentication flows
- Main page requests

#### Background Services (`src/booking/scheduler.py`, `src/booking/email_service.py`)
- Scheduler operations
- Email sending operations
- Report generation

## Features

### 1. Filtering and Search
- **Level Filtering**: Filter logs by severity level
- **Logger Filtering**: Filter by specific application components
- **Time Range Filtering**: View logs from specific time periods
- **Text Search**: Search within log messages
- **User Filtering**: View logs associated with specific users

### 2. Log Statistics
- **Real-time Stats**: Total logs and error counts for last 24 hours
- **Top Loggers**: Most active logging components
- **Level Distribution**: Breakdown of logs by severity level

### 3. Log Management
- **Pagination**: Efficient loading of large log datasets
- **Detailed View**: Modal with complete log information including:
  - Full message text
  - Stack traces for exceptions
  - Context data (JSON formatted)
  - User information
  - Request tracing information
- **Cleanup**: Remove old logs to manage database size

### 4. Context-Aware Logging
- **User Context**: Logs can be associated with specific users
- **Request Tracing**: Support for request IDs to trace operations
- **Extra Data**: JSON storage for additional context information
- **Exception Details**: Full stack traces and exception information

## Security Considerations
- **Admin Only**: All log viewing functionality requires admin privileges
- **Data Sanitization**: Sensitive information should not be logged
- **Access Control**: Proper authentication and authorization for log access

## Performance Considerations
- **Database Indexing**: Indexes on timestamp, level, and logger_name for efficient filtering
- **Pagination**: Prevents loading too many logs at once
- **Cleanup Functionality**: Prevents unlimited log growth
- **Async Logging**: Database logging doesn't block application operations

## Usage Examples

### Viewing Logs in Admin Interface
1. Login as an admin user
2. Navigate to the "Application Logs" tab
3. Use filters to narrow down logs:
   - Select log level (ERROR to see only errors)
   - Choose time range for specific periods
   - Search for specific text in messages
4. Click "Details" on any log to see complete information

### Programmatic Logging
```python
from src.booking.logging_config import get_logger, log_with_context
import logging

logger = get_logger("my_component")

# Basic logging
logger.info("User performed action")

# Logging with context
log_with_context(
    logger, logging.WARNING,
    "Potential security issue detected",
    user_id=user.id,
    extra_data={"ip_address": "192.168.1.1", "action": "failed_login"}
)
```

### API Usage
```bash
# Get recent logs
curl -H "Authorization: Bearer <token>" \
     "http://localhost:8000/api/admin/logs?limit=50"

# Get error logs from last hour
curl -H "Authorization: Bearer <token>" \
     "http://localhost:8000/api/admin/logs?level=ERROR&start_time=2023-01-01T10:00:00"

# Get log statistics
curl -H "Authorization: Bearer <token>" \
     "http://localhost:8000/api/admin/logs/stats?hours=24"
```

## Testing
- **test_logging.py**: Tests basic logging functionality and database storage
- **test_logs_api.py**: Tests the admin API endpoints
- All logging functionality has been tested and verified working

## Future Enhancements
- **Log Aggregation**: Group similar logs together
- **Alerting**: Email/SMS alerts for critical errors
- **Log Export**: Export logs to CSV/JSON formats
- **Real-time Updates**: WebSocket updates for live log viewing
- **Log Retention Policies**: Automatic cleanup based on configurable rules
- **Performance Metrics**: Track application performance through logs