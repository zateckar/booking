"""
Email service for sending booking confirmations and reports using SendGrid API
"""
import json
import logging
import requests
import ssl
import urllib3
import pytz
from datetime import datetime, timezone, timedelta
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session

from . import models, schemas
from .logging_config import get_logger

logger = get_logger("email_service")


class EmailServiceError(Exception):
    """Raised when email service encounters an error"""
    pass


class EmailService:
    """Service for handling email operations with SendGrid"""
    
    def __init__(self, db: Session):
        self.db = db
        self._settings = None
        self._client = None
    
    def _get_settings(self) -> Optional[models.EmailSettings]:
        """Get email settings from database"""
        if not self._settings:
            self._settings = self.db.query(models.EmailSettings).first()
        return self._settings
    
    def _send_email_request(self, email_data: Dict[str, Any]) -> Dict[str, Any]:
        """Send email via direct HTTP request to SendGrid API"""
        settings = self._get_settings()
        if not settings or not settings.sendgrid_api_key:
            return {'success': False, 'error': 'No API key configured'}
        
        # Disable SSL verification and warnings for development environments
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
        
        headers = {
            'Authorization': f'Bearer {settings.sendgrid_api_key}',
            'Content-Type': 'application/json'
        }
        
        url = 'https://api.sendgrid.com/v3/mail/send'
        
        try:
            # Create session with SSL verification disabled
            session = requests.Session()
            session.verify = False
            
            response = session.post(url, headers=headers, json=email_data, timeout=30)
            
            return {
                'success': response.status_code in [200, 202],
                'status_code': response.status_code,
                'response_text': response.text
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    def _refresh_settings(self):
        """Refresh cached settings and client"""
        self._settings = None
        self._client = None
    
    def _format_datetime_in_timezone(self, dt: datetime, format_str: str = "%d-%m-%Y %H:%M") -> str:
        """
        Format datetime in the configured timezone with consistent format
        
        Args:
            dt: UTC datetime to format
            format_str: Format string for datetime (default: "DD-MM-YYYY HH:MM" in 24h format)
            
        Returns:
            Formatted datetime string without timezone designator
        """
        from .timezone_service import TimezoneService
        
        timezone_service = TimezoneService(self.db)
        return timezone_service.format_datetime_local(dt, format_str, include_tz=False)
    
    def send_booking_confirmation(self, booking: models.Booking) -> bool:
        """
        Send booking confirmation email to user
        
        Args:
            booking: The booking to send confirmation for
            
        Returns:
            True if email sent successfully, False otherwise
        """
        try:
            settings = self._get_settings()
            if not settings or not settings.booking_confirmation_enabled:
                logger.info("Booking confirmation emails are disabled")
                return False
            
            if not settings.sendgrid_api_key:
                logger.error("SendGrid API key not configured")
                return False
            
            # Get booking details
            user = booking.user
            space = booking.space
            parking_lot = space.parking_lot
            
            # Format dates for display in configured timezone
            start_local = self._format_datetime_in_timezone(booking.start_time)
            end_local = self._format_datetime_in_timezone(booking.end_time)
            
            # Create email content
            subject = f"Booking Confirmation - {parking_lot.name}"
            
            html_content = f"""
            <html>
            <body>
                <h2>Booking Confirmation</h2>
                <p>Dear {user.email},</p>
                <p>Your parking booking has been confirmed with the following details:</p>
                
                <div style="background-color: #f5f5f5; padding: 15px; border-radius: 5px; margin: 20px 0;">
                    <h3>Booking Details</h3>
                    <p><strong>Booking ID:</strong> #{booking.id}</p>
                    <p><strong>Parking Lot:</strong> {parking_lot.name}</p>
                    <p><strong>Space Number:</strong> {space.space_number}</p>
                    <p><strong>License Plate:</strong> {booking.license_plate}</p>
                    <p><strong>Start Time:</strong> {start_local}</p>
                    <p><strong>End Time:</strong> {end_local}</p>
                </div>
                
                <p>Please arrive on time and display your license plate clearly.</p>
                <p>If you need to cancel or modify your booking, please contact us as soon as possible.</p>
                
                <p>Thank you for using our parking booking system!</p>
                
                <p>Best regards,<br>
                {settings.from_name}</p>
            </body>
            </html>
            """
            
            plain_content = f"""
            Booking Confirmation
            
            Dear {user.email},
            
            Your parking booking has been confirmed with the following details:
            
            Booking ID: #{booking.id}
            Parking Lot: {parking_lot.name}
            Space Number: {space.space_number}
            License Plate: {booking.license_plate}
            Start Time: {start_local}
            End Time: {end_local}
            
            Please arrive on time and display your license plate clearly.
            If you need to cancel or modify your booking, please contact us as soon as possible.
            
            Thank you for using our parking booking system!
            
            Best regards,
            {settings.from_name}
            """
            
            # Create email data for SendGrid API
            email_data = {
                "personalizations": [{
                    "to": [{"email": user.email}],
                    "subject": subject
                }],
                "from": {
                    "email": settings.from_email,
                    "name": settings.from_name
                },
                "content": [
                    {
                        "type": "text/plain",
                        "value": plain_content
                    },
                    {
                        "type": "text/html",
                        "value": html_content
                    }
                ]
            }
            
            # Send email via direct HTTP request
            result = self._send_email_request(email_data)
            
            if result['success']:
                logger.info(f"Booking confirmation sent successfully to {user.email}")
                return True
            else:
                logger.error(f"Failed to send booking confirmation: {result.get('error', 'Unknown error')}")
                return False
                
        except Exception as e:
            logger.error(f"Error sending booking confirmation: {str(e)}")
            return False
    
    def generate_booking_report(self, start_date: datetime, end_date: datetime) -> Dict[str, Any]:
        """
        Generate booking report data for a date range
        
        Args:
            start_date: Start date for report
            end_date: End date for report
            
        Returns:
            Dictionary containing report data
        """
        # Get all bookings in date range
        bookings = self.db.query(models.Booking).filter(
            models.Booking.start_time >= start_date,
            models.Booking.start_time < end_date
        ).all()
        
        # Get all parking lots for context
        parking_lots = self.db.query(models.ParkingLot).all()
        lot_names = {lot.id: lot.name for lot in parking_lots}
        
        # Calculate statistics
        total_bookings = len(bookings)
        active_bookings = len([b for b in bookings if not b.is_cancelled])
        cancelled_bookings = len([b for b in bookings if b.is_cancelled])
        
        # Group by parking lot
        lot_stats = {}
        for booking in bookings:
            lot_id = booking.space.lot_id
            lot_name = lot_names.get(lot_id, f"Lot {lot_id}")
            
            if lot_name not in lot_stats:
                lot_stats[lot_name] = {
                    'total': 0,
                    'active': 0,
                    'cancelled': 0
                }
            
            lot_stats[lot_name]['total'] += 1
            if booking.is_cancelled:
                lot_stats[lot_name]['cancelled'] += 1
            else:
                lot_stats[lot_name]['active'] += 1
        
        # Get unique users
        unique_users = len(set(booking.user_id for booking in bookings))
        
        return {
            'period': {
                'start': start_date.strftime("%Y-%m-%d"),
                'end': end_date.strftime("%Y-%m-%d")
            },
            'summary': {
                'total_bookings': total_bookings,
                'active_bookings': active_bookings,
                'cancelled_bookings': cancelled_bookings,
                'unique_users': unique_users
            },
            'by_parking_lot': lot_stats,
            'recent_bookings': [
                {
                    'id': b.id,
                    'user_email': b.user.email,
                    'parking_lot': lot_names.get(b.space.lot_id, f"Lot {b.space.lot_id}"),
                    'space_number': b.space.space_number,
                    'start_time': self._format_datetime_in_timezone(b.start_time),
                    'license_plate': b.license_plate,
                    'status': 'Cancelled' if b.is_cancelled else 'Active'
                }
                for b in sorted(bookings, key=lambda x: x.start_time, reverse=True)[:10]
            ]
        }
    
    def send_booking_report(self, force_send: bool = False) -> bool:
        """
        Send periodic booking report to configured recipients
        
        Args:
            force_send: If True, send report regardless of schedule
            
        Returns:
            True if report sent successfully, False otherwise
        """
        try:
            settings = self._get_settings()
            if not settings or not settings.reports_enabled:
                logger.info("Booking reports are disabled")
                return False
            
            if not settings.report_recipients:
                logger.info("No report recipients configured")
                return False
            
            if not settings.sendgrid_api_key:
                logger.error("SendGrid API key not configured")
                return False
            
            # Parse recipients from JSON string
            try:
                recipients = json.loads(settings.report_recipients) if isinstance(settings.report_recipients, str) else settings.report_recipients
            except (json.JSONDecodeError, TypeError):
                logger.error("Invalid report recipients format")
                return False
            
            if not recipients:
                logger.info("No report recipients configured")
                return False
            
            # Check if we should send report based on schedule
            now = datetime.now(timezone.utc)
            if not force_send and settings.last_report_sent:
                time_since_last = now - settings.last_report_sent
                
                if settings.report_frequency == "daily" and time_since_last < timedelta(hours=23):
                    logger.info("Daily report already sent recently")
                    return False
                elif settings.report_frequency == "weekly" and time_since_last < timedelta(days=6):
                    logger.info("Weekly report already sent recently")
                    return False
                elif settings.report_frequency == "monthly" and time_since_last < timedelta(days=29):
                    logger.info("Monthly report already sent recently")
                    return False
            
            # Determine report period
            if settings.report_frequency == "daily":
                start_date = now.replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=1)
                end_date = start_date + timedelta(days=1)
                period_name = "Daily"
            elif settings.report_frequency == "weekly":
                days_since_monday = now.weekday()
                start_date = now.replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=days_since_monday + 7)
                end_date = start_date + timedelta(days=7)
                period_name = "Weekly"
            else:  # monthly
                start_date = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
                if start_date.month == 1:
                    start_date = start_date.replace(year=start_date.year - 1, month=12)
                else:
                    start_date = start_date.replace(month=start_date.month - 1)
                
                # Get last day of previous month
                if start_date.month == 12:
                    end_date = start_date.replace(year=start_date.year + 1, month=1)
                else:
                    end_date = start_date.replace(month=start_date.month + 1)
                period_name = "Monthly"
            
            # Generate report data
            report_data = self.generate_booking_report(start_date, end_date)
            
            # Create email content
            subject = f"{period_name} Parking Booking Report - {report_data['period']['start']} to {report_data['period']['end']}"
            
            html_content = f"""
            <html>
            <body>
                <h2>{period_name} Parking Booking Report</h2>
                <p>Report Period: {report_data['period']['start']} to {report_data['period']['end']}</p>
                
                <div style="background-color: #f5f5f5; padding: 15px; border-radius: 5px; margin: 20px 0;">
                    <h3>Summary</h3>
                    <p><strong>Total Bookings:</strong> {report_data['summary']['total_bookings']}</p>
                    <p><strong>Active Bookings:</strong> {report_data['summary']['active_bookings']}</p>
                    <p><strong>Cancelled Bookings:</strong> {report_data['summary']['cancelled_bookings']}</p>
                    <p><strong>Unique Users:</strong> {report_data['summary']['unique_users']}</p>
                </div>
                
                <div style="background-color: #f9f9f9; padding: 15px; border-radius: 5px; margin: 20px 0;">
                    <h3>Bookings by Parking Lot</h3>
                    <table style="width: 100%; border-collapse: collapse;">
                        <tr style="background-color: #e0e0e0;">
                            <th style="padding: 8px; text-align: left; border: 1px solid #ccc;">Parking Lot</th>
                            <th style="padding: 8px; text-align: left; border: 1px solid #ccc;">Total</th>
                            <th style="padding: 8px; text-align: left; border: 1px solid #ccc;">Active</th>
                            <th style="padding: 8px; text-align: left; border: 1px solid #ccc;">Cancelled</th>
                        </tr>
            """
            
            for lot_name, stats in report_data['by_parking_lot'].items():
                html_content += f"""
                        <tr>
                            <td style="padding: 8px; border: 1px solid #ccc;">{lot_name}</td>
                            <td style="padding: 8px; border: 1px solid #ccc;">{stats['total']}</td>
                            <td style="padding: 8px; border: 1px solid #ccc;">{stats['active']}</td>
                            <td style="padding: 8px; border: 1px solid #ccc;">{stats['cancelled']}</td>
                        </tr>
                """
            
            html_content += """
                    </table>
                </div>
                
                <div style="background-color: #f0f8ff; padding: 15px; border-radius: 5px; margin: 20px 0;">
                    <h3>Recent Bookings</h3>
                    <table style="width: 100%; border-collapse: collapse;">
                        <tr style="background-color: #e0e0e0;">
                            <th style="padding: 8px; text-align: left; border: 1px solid #ccc;">ID</th>
                            <th style="padding: 8px; text-align: left; border: 1px solid #ccc;">User</th>
                            <th style="padding: 8px; text-align: left; border: 1px solid #ccc;">Parking Lot</th>
                            <th style="padding: 8px; text-align: left; border: 1px solid #ccc;">Space</th>
                            <th style="padding: 8px; text-align: left; border: 1px solid #ccc;">Start Time</th>
                            <th style="padding: 8px; text-align: left; border: 1px solid #ccc;">Status</th>
                        </tr>
            """
            
            for booking in report_data['recent_bookings']:
                html_content += f"""
                        <tr>
                            <td style="padding: 8px; border: 1px solid #ccc;">#{booking['id']}</td>
                            <td style="padding: 8px; border: 1px solid #ccc;">{booking['user_email']}</td>
                            <td style="padding: 8px; border: 1px solid #ccc;">{booking['parking_lot']}</td>
                            <td style="padding: 8px; border: 1px solid #ccc;">{booking['space_number']}</td>
                            <td style="padding: 8px; border: 1px solid #ccc;">{booking['start_time']}</td>
                            <td style="padding: 8px; border: 1px solid #ccc;">{booking['status']}</td>
                        </tr>
                """
            
            html_content += f"""
                    </table>
                </div>
                
                <p>This report was generated automatically by the parking booking system.</p>
                
                <p>Best regards,<br>
                {settings.from_name}</p>
            </body>
            </html>
            """
            
            # Create plain text version
            plain_content = f"""
            {period_name} Parking Booking Report
            Report Period: {report_data['period']['start']} to {report_data['period']['end']}
            
            SUMMARY
            Total Bookings: {report_data['summary']['total_bookings']}
            Active Bookings: {report_data['summary']['active_bookings']}
            Cancelled Bookings: {report_data['summary']['cancelled_bookings']}
            Unique Users: {report_data['summary']['unique_users']}
            
            BOOKINGS BY PARKING LOT
            """
            
            for lot_name, stats in report_data['by_parking_lot'].items():
                plain_content += f"{lot_name}: {stats['total']} total ({stats['active']} active, {stats['cancelled']} cancelled)\n"
            
            plain_content += f"""
            
            RECENT BOOKINGS
            """
            
            for booking in report_data['recent_bookings']:
                plain_content += f"#{booking['id']} - {booking['user_email']} - {booking['parking_lot']} {booking['space_number']} - {booking['start_time']} - {booking['status']}\n"
            
            plain_content += f"""
            
            This report was generated automatically by the parking booking system.
            
            Best regards,
            {settings.from_name}
            """
            
            # Send to all recipients
            success_count = 0
            for recipient in recipients:
                try:
                    # Create email data for SendGrid API
                    email_data = {
                        "personalizations": [{
                            "to": [{"email": recipient}],
                            "subject": subject
                        }],
                        "from": {
                            "email": settings.from_email,
                            "name": settings.from_name
                        },
                        "content": [
                            {
                                "type": "text/plain",
                                "value": plain_content
                            },
                            {
                                "type": "text/html",
                                "value": html_content
                            }
                        ]
                    }
                    
                    result = self._send_email_request(email_data)
                    
                    if result['success']:
                        success_count += 1
                        logger.info(f"Report sent successfully to {recipient}")
                    else:
                        logger.error(f"Failed to send report to {recipient}: {result.get('error', 'Unknown error')}")
                        
                except Exception as e:
                    logger.error(f"Error sending report to {recipient}: {str(e)}")
            
            # Update last report sent time if at least one email was successful
            if success_count > 0:
                settings.last_report_sent = now
                self.db.commit()
                logger.info(f"Report sent to {success_count}/{len(recipients)} recipients")
                return True
            else:
                logger.error("Failed to send report to any recipients")
                return False
                
        except Exception as e:
            logger.error(f"Error sending booking report: {str(e)}")
            return False
    
    def test_email_configuration(self) -> Dict[str, Any]:
        """
        Test email configuration by sending a test email
        
        Returns:
            Dictionary with test results
        """
        try:
            settings = self._get_settings()
            if not settings:
                return {
                    'success': False,
                    'error': 'No email settings configured'
                }
            
            if not settings.sendgrid_api_key:
                return {
                    'success': False,
                    'error': 'SendGrid API key not configured'
                }
            
            if not settings.from_email:
                return {
                    'success': False,
                    'error': 'From email not configured'
                }
            
            # Create email data for SendGrid API
            email_data = {
                "personalizations": [{
                    "to": [{"email": settings.from_email}],
                    "subject": "Test Email - Parking Booking System"
                }],
                "from": {
                    "email": settings.from_email,
                    "name": settings.from_name
                },
                "content": [
                    {
                        "type": "text/plain",
                        "value": """
                        Test Email
                        
                        This is a test email from your parking booking system.
                        If you received this email, your SendGrid configuration is working correctly!
                        """
                    },
                    {
                        "type": "text/html",
                        "value": """
                        <html>
                        <body>
                            <h2>Test Email</h2>
                            <p>This is a test email from your parking booking system.</p>
                            <p>If you received this email, your SendGrid configuration is working correctly!</p>
                        </body>
                        </html>
                        """
                    }
                ]
            }
            
            result = self._send_email_request(email_data)
            
            if result['success']:
                return {
                    'success': True,
                    'message': f'Test email sent successfully to {settings.from_email}'
                }
            else:
                return {
                    'success': False,
                    'error': f'SendGrid API error: {result.get("error", "Unknown error")}'
                }
                
        except Exception as e:
            return {
                'success': False,
                'error': f'Error testing email configuration: {str(e)}'
            }