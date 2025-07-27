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
            # Static reports have been removed - this method is no longer used
            logger.info("Static booking reports have been removed. Use Dynamic Reports instead.")
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
