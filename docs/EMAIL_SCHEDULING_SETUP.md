# Email Scheduling Setup and Troubleshooting Guide

## Overview

The parking booking system includes an automated email scheduling feature that sends periodic booking reports to configured recipients. This guide explains how the system works and how to ensure it's functioning properly.

## How Email Scheduling Works

### Components

1. **EmailService** (`src/booking/email_service.py`)
   - Handles email sending via SendGrid API
   - Generates booking reports with statistics
   - Supports manual and scheduled sending

2. **ReportScheduler** (`src/booking/scheduler.py`)
   - Background task that runs continuously
   - Checks every 10 minutes if reports should be sent
   - Respects timezone settings and frequency rules

3. **Email Settings** (Database configuration)
   - Stored in `email_settings` table
   - Configurable via admin interface
   - Includes schedule, recipients, and preferences

### Scheduling Logic

The scheduler sends reports based on:
- **Time**: Reports are sent at the configured hour in the specified timezone
- **Frequency**: Daily, weekly, or monthly intervals
- **Last Sent**: Prevents duplicate sends within the same period

## Configuration

### Required Settings

1. **SendGrid API Key**: Valid API key for email sending
2. **From Email**: Sender email address
3. **Recipients**: JSON array of recipient email addresses
4. **Schedule Hour**: Hour of day to send reports (0-23)
5. **Timezone**: Timezone for scheduling (e.g., "Europe/Prague")
6. **Frequency**: "daily", "weekly", or "monthly"

### Example Configuration

```json
{
  "reports_enabled": true,
  "sendgrid_api_key": "SG.your-api-key-here",
  "from_email": "reports@yourcompany.com",
  "from_name": "Parking Booking System",
  "report_recipients": ["admin@yourcompany.com", "manager@yourcompany.com"],
  "report_schedule_hour": 9,
  "report_frequency": "daily",
  "timezone": "Europe/Prague"
}
```

## Running the Scheduler

### Option 1: With FastAPI Application (Recommended)

The scheduler starts automatically when you run the main application:

```bash
python run.py
# or
uvicorn src.booking:app --host 0.0.0.0 --port 8000
```

### Option 2: Standalone Scheduler Service

For production environments, you can run the scheduler independently:

```bash
python run_scheduler.py
```

This creates a dedicated service that:
- Runs independently of the web application
- Logs to both console and `scheduler.log` file
- Handles graceful shutdown with Ctrl+C
- Automatically restarts on errors

## Troubleshooting

### 1. Check if Scheduler is Running

```bash
python monitor_scheduler.py
```

This will show:
- Current email settings
- Time status and schedule matching
- Scheduler running status
- Diagnostic information

### 2. Test Email Configuration

```bash
python test_scheduler_manual.py test
```

This will:
- Test manual email sending
- Verify scheduler logic
- Show detailed timing information

### 3. Force Send Report

```bash
python test_scheduler_manual.py force
```

This bypasses all scheduling rules and sends a report immediately.

### 4. Reset Last Sent Time

```bash
python test_scheduler_manual.py reset
```

This resets the last sent time to allow immediate testing.

## Common Issues and Solutions

### Issue: Reports Not Being Sent

**Possible Causes:**
1. Scheduler not running
2. Wrong timezone configuration
3. Reports already sent today
4. Invalid email settings

**Solutions:**
1. Ensure FastAPI app is running or start standalone scheduler
2. Check timezone matches your local timezone
3. Wait for next scheduled time or reset last sent time
4. Test email configuration in admin interface

### Issue: Wrong Send Time

**Cause:** Timezone mismatch between server and configuration

**Solution:** 
- Set correct timezone in email settings
- Verify server timezone with `python -c "import datetime; print(datetime.datetime.now())"`

### Issue: Multiple Reports Sent

**Cause:** Scheduler restarting frequently (development mode)

**Solution:**
- Use standalone scheduler for production
- Check logs for restart patterns
- Ensure stable server environment

### Issue: Email Delivery Failures

**Possible Causes:**
1. Invalid SendGrid API key
2. Sender email not verified
3. Recipient email issues
4. Network connectivity

**Solutions:**
1. Verify API key in SendGrid dashboard
2. Verify sender email in SendGrid
3. Check recipient email addresses
4. Test with manual send

## Monitoring and Logs

### Log Files

- **Application logs**: Check FastAPI application logs
- **Scheduler logs**: `scheduler.log` (when using standalone service)

### Key Log Messages

- `"Scheduler loop started"`: Scheduler is running
- `"Scheduled report sent successfully"`: Report sent
- `"Report sending skipped"`: Scheduling rules prevented send
- `"Failed to send scheduled report"`: Email delivery failed

### Monitoring Commands

```bash
# Check current status
python monitor_scheduler.py

# Run comprehensive test
python test_complete_scheduler.py

# Monitor logs in real-time
tail -f scheduler.log
```

## Production Deployment

### Recommended Setup

1. **Use Standalone Scheduler**:
   ```bash
   python run_scheduler.py &
   ```

2. **Set up Process Manager** (e.g., systemd, supervisor):
   ```ini
   [program:booking-scheduler]
   command=python /path/to/booking/run_scheduler.py
   directory=/path/to/booking
   autostart=true
   autorestart=true
   user=booking
   ```

3. **Configure Log Rotation**:
   ```bash
   logrotate -d /etc/logrotate.d/booking-scheduler
   ```

### Environment Variables

Consider using environment variables for sensitive settings:

```bash
export SENDGRID_API_KEY="your-api-key"
export REPORT_RECIPIENTS="admin@company.com,manager@company.com"
```

## Testing Checklist

Before deploying to production:

- [ ] Email settings configured correctly
- [ ] SendGrid API key valid and tested
- [ ] Recipients can receive emails
- [ ] Timezone set correctly
- [ ] Schedule hour appropriate for business needs
- [ ] Scheduler starts with application
- [ ] Manual report sending works
- [ ] Logs are being written
- [ ] Error handling works (test with invalid settings)

## Support

If you continue to experience issues:

1. Check all configuration settings
2. Review log files for errors
3. Test individual components (email, scheduler, database)
4. Verify network connectivity and API access
5. Consider running in debug mode for detailed logging

The email scheduling system is designed to be robust and self-healing, but proper configuration and monitoring are essential for reliable operation.