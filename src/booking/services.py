"""
Booking service layer for enhanced conflict resolution and validation
"""
from datetime import datetime, timezone, timedelta
import pytz
import logging
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func

from . import models, schemas
from .email_service import EmailService
from .timezone_service import TimezoneService
from .logging_config import get_logger, log_with_context

logger = get_logger("services.booking")


class BookingConflictError(Exception):
    """Raised when a booking conflict is detected"""
    pass


class BookingValidationError(Exception):
    """Raised when booking validation fails"""
    pass


class BookingService:
    """Service class for booking operations with enhanced validation and conflict resolution"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def check_booking_conflicts(
        self, 
        space_id: int, 
        start_time: datetime, 
        end_time: datetime,
        exclude_booking_id: Optional[int] = None
    ) -> List[models.Booking]:
        """
        Check for booking conflicts with enhanced validation
        
        Args:
            space_id: ID of the parking space
            start_time: Proposed booking start time
            end_time: Proposed booking end time
            exclude_booking_id: Optional booking ID to exclude from conflict check (for updates)
            
        Returns:
            List of conflicting bookings
        """
        # Ensure times are timezone-aware
        if start_time.tzinfo is None:
            start_time = start_time.replace(tzinfo=timezone.utc)
        if end_time.tzinfo is None:
            end_time = end_time.replace(tzinfo=timezone.utc)
        
        # Build conflict query
        conflict_query = self.db.query(models.Booking).filter(
            models.Booking.space_id == space_id,
            models.Booking.is_cancelled == False,
            # Check for time overlap: (start1 < end2) AND (end1 > start2)
            models.Booking.start_time < end_time,
            models.Booking.end_time > start_time
        )
        
        # Exclude specific booking if provided (for updates)
        if exclude_booking_id:
            conflict_query = conflict_query.filter(
                models.Booking.id != exclude_booking_id
            )
        
        return conflict_query.all()
    
    def validate_booking_business_rules(
        self, 
        space_id: int, 
        start_time: datetime, 
        end_time: datetime,
        user_id: int,
        exclude_booking_id: Optional[int] = None,
        timezone_name: Optional[str] = None
    ) -> None:
        """
        Validate business rules for booking creation with enhanced edge case handling
        
        Args:
            space_id: ID of the parking space
            start_time: Booking start time
            end_time: Booking end time
            user_id: ID of the user making the booking
            exclude_booking_id: Optional booking ID to exclude from validation (for updates)
            timezone_name: Timezone name for local time validation (default: UTC)
            
        Raises:
            BookingValidationError: If validation fails
        """
        # Ensure times are timezone-aware
        if start_time.tzinfo is None:
            start_time = start_time.replace(tzinfo=timezone.utc)
        if end_time.tzinfo is None:
            end_time = end_time.replace(tzinfo=timezone.utc)
        
        # Check if parking space exists and is active
        space = self.db.query(models.ParkingSpace).filter(
            models.ParkingSpace.id == space_id
        ).first()
        if not space:
            raise BookingValidationError(f"Parking space {space_id} does not exist")
            
        # Get the parking lot to determine location-specific rules
        parking_lot = self.db.query(models.ParkingLot).filter(
            models.ParkingLot.id == space.lot_id
        ).first()
        if not parking_lot:
            raise BookingValidationError(f"Parking lot for space {space_id} does not exist")
        
        # Validate time range constraints
        now = datetime.now(timezone.utc)
        
        # Check for excessive future bookings (prevent booking more than 30 days ahead)
        max_future_booking = now + timedelta(days=30)
        if start_time > max_future_booking:
            raise BookingValidationError("Cannot book more than 30 days in advance")
        
        # Check for bookings too far in the past (allow 5 minutes grace period)
        grace_period = now - timedelta(minutes=5)
        if start_time < grace_period:
            raise BookingValidationError("Cannot create bookings more than 5 minutes in the past")
        
        # Validate booking duration constraints
        duration = end_time - start_time
        if duration.total_seconds() < 900:  # 15 minutes
            raise BookingValidationError("Booking duration must be at least 15 minutes")
        
        if duration.total_seconds() > 86400:  # 24 hours
            raise BookingValidationError("Booking duration cannot exceed 24 hours")
        
        # Use timezone service for business hour validation
        timezone_service = TimezoneService(self.db)
        if timezone_name is None:
            timezone_name = timezone_service.get_system_timezone()
        
        # Convert to local time for business hour validation
        local_start = timezone_service.convert_utc_to_local(start_time, timezone_name)
        local_end = timezone_service.convert_utc_to_local(end_time, timezone_name)
        
        # Check for reasonable booking hours (6 AM to 11 PM local time)
        start_hour = local_start.hour
        end_hour = local_end.hour
        
        if start_hour < 6 or start_hour > 23:
            tz_display = timezone_name.replace('_', ' ')
            raise BookingValidationError(f"Bookings can only start between 6:00 AM and 11:00 PM {tz_display} time")
        
        # Allow overnight bookings but end time must be reasonable next day
        if end_hour > 23 and local_end.date() == local_start.date():
            tz_display = timezone_name.replace('_', ' ')
            raise BookingValidationError(f"Same-day bookings must end by 11:00 PM {tz_display} time")
        
        if local_end.date() > local_start.date() and end_hour > 11:
            tz_display = timezone_name.replace('_', ' ')
            raise BookingValidationError(f"Overnight bookings must end by 11:00 AM {tz_display} time the next day")
        
        # Check user's concurrent booking limit (max 5 active bookings per user)
        active_bookings_query = self.db.query(models.Booking).filter(
            models.Booking.user_id == user_id,
            models.Booking.is_cancelled == False,
            models.Booking.end_time > now
        )
        
        if exclude_booking_id:
            active_bookings_query = active_bookings_query.filter(
                models.Booking.id != exclude_booking_id
            )
        
        active_bookings_count = active_bookings_query.count()
        if active_bookings_count >= 5:
            raise BookingValidationError("Maximum of 5 active bookings allowed per user")
        
        # Check for same-day multiple bookings by same user (prevent abuse)
        start_date = start_time.date()
        same_day_query = self.db.query(models.Booking).filter(
            models.Booking.user_id == user_id,
            models.Booking.is_cancelled == False,
            models.Booking.start_time >= datetime.combine(start_date, datetime.min.time()).replace(tzinfo=timezone.utc),
            models.Booking.start_time < datetime.combine(start_date + timedelta(days=1), datetime.min.time()).replace(tzinfo=timezone.utc)
        )
        
        if exclude_booking_id:
            same_day_query = same_day_query.filter(
                models.Booking.id != exclude_booking_id
            )
        
        same_day_bookings = same_day_query.count()
        if same_day_bookings >= 3:
            raise BookingValidationError("Maximum of 3 bookings per day allowed per user")
        
        # Check for overlapping bookings by same user (prevent double-booking)
        user_overlap_query = self.db.query(models.Booking).filter(
            models.Booking.user_id == user_id,
            models.Booking.is_cancelled == False,
            models.Booking.start_time < end_time,
            models.Booking.end_time > start_time
        )
        
        if exclude_booking_id:
            user_overlap_query = user_overlap_query.filter(
                models.Booking.id != exclude_booking_id
            )
        
        overlapping_user_bookings = user_overlap_query.all()
        if overlapping_user_bookings:
            raise BookingValidationError("You already have a booking during this time period")
        
        # Check for rapid successive bookings (prevent system abuse)
        recent_bookings = self.db.query(models.Booking).filter(
            models.Booking.user_id == user_id,
            models.Booking.start_time >= now - timedelta(minutes=5),
            models.Booking.start_time <= now + timedelta(minutes=5)
        )
        
        if exclude_booking_id:
            recent_bookings = recent_bookings.filter(
                models.Booking.id != exclude_booking_id
            )
        
        if recent_bookings.count() >= 3:
            raise BookingValidationError("Too many bookings created recently. Please wait before creating another booking.")
    
    def create_booking_with_validation(
        self, 
        booking_data: schemas.BookingCreate, 
        user_id: int
    ) -> models.Booking:
        """
        Create a booking with comprehensive validation and conflict resolution
        
        Args:
            booking_data: Booking creation data
            user_id: ID of the user creating the booking
            
        Returns:
            Created booking
            
        Raises:
            BookingConflictError: If booking conflicts exist
            BookingValidationError: If validation fails
        """
        log_with_context(
            logger, logging.DEBUG,
            f"Starting booking validation for space {booking_data.space_id}",
            user_id=user_id,
            extra_data={
                "space_id": booking_data.space_id,
                "start_time": booking_data.start_time.isoformat(),
                "end_time": booking_data.end_time.isoformat()
            }
        )
        
        # Validate business rules
        self.validate_booking_business_rules(
            booking_data.space_id,
            booking_data.start_time,
            booking_data.end_time,
            user_id
        )
        
        # Check for conflicts
        conflicts = self.check_booking_conflicts(
            booking_data.space_id,
            booking_data.start_time,
            booking_data.end_time
        )
        
        if conflicts:
            conflict_details = []
            for conflict in conflicts:
                conflict_details.append(
                    f"Booking {conflict.id} from {conflict.start_time} to {conflict.end_time}"
                )
            
            log_with_context(
                logger, logging.WARNING,
                f"Booking conflicts detected for space {booking_data.space_id}",
                user_id=user_id,
                extra_data={"conflicts": conflict_details}
            )
            
            raise BookingConflictError(
                f"Booking conflicts detected: {'; '.join(conflict_details)}"
            )
        
        # Create the booking
        db_booking = models.Booking(
            space_id=booking_data.space_id,
            user_id=user_id,
            start_time=booking_data.start_time,
            end_time=booking_data.end_time,
            license_plate=booking_data.license_plate,
            is_cancelled=False
        )
        
        self.db.add(db_booking)
        self.db.commit()
        self.db.refresh(db_booking)
        
        log_with_context(
            logger, logging.INFO,
            f"Successfully created booking {db_booking.id} for space {booking_data.space_id}",
            user_id=user_id,
            extra_data={
                "booking_id": db_booking.id,
                "space_id": booking_data.space_id,
                "license_plate": booking_data.license_plate
            }
        )
        
        # Send booking confirmation email
        try:
            email_service = EmailService(self.db)
            email_service.send_booking_confirmation(db_booking)
            logger.debug(f"Booking confirmation email sent for booking {db_booking.id}")
        except Exception as e:
            # Log error but don't fail the booking creation
            log_with_context(
                logger, logging.ERROR,
                f"Failed to send booking confirmation email for booking {db_booking.id}: {str(e)}",
                user_id=user_id,
                extra_data={"booking_id": db_booking.id, "error": str(e)}
            )
        
        return db_booking
    
    def update_booking_with_validation(
        self, 
        booking_id: int, 
        booking_update: schemas.BookingUpdate,
        user_id: int
    ) -> models.Booking:
        """
        Update a booking with validation and conflict resolution
        
        Args:
            booking_id: ID of the booking to update
            booking_update: Update data
            user_id: ID of the user updating the booking
            
        Returns:
            Updated booking
            
        Raises:
            BookingConflictError: If booking conflicts exist
            BookingValidationError: If validation fails
        """
        # Get existing booking
        existing_booking = self.db.query(models.Booking).filter(
            models.Booking.id == booking_id
        ).first()
        
        if not existing_booking:
            raise BookingValidationError(f"Booking {booking_id} not found")
        
        # Check if user owns the booking or is admin
        user = self.db.query(models.User).filter(models.User.id == user_id).first()
        if not user:
            raise BookingValidationError("User not found")
        
        if existing_booking.user_id != user_id and not user.is_admin:
            raise BookingValidationError("Not authorized to update this booking")
        
        # Check if booking can be modified (not in the past and not cancelled)
        now = datetime.now(timezone.utc)
        if existing_booking.start_time < now:
            raise BookingValidationError("Cannot modify bookings that have already started")
        
        if existing_booking.is_cancelled:
            raise BookingValidationError("Cannot modify cancelled bookings")
        
        # Apply updates
        updated_start = booking_update.start_time or existing_booking.start_time
        updated_end = booking_update.end_time or existing_booking.end_time
        updated_license_plate = booking_update.license_plate or existing_booking.license_plate
        
        # Validate updated times if they changed
        if (booking_update.start_time or booking_update.end_time):
            # Ensure times are timezone-aware
            if updated_start.tzinfo is None:
                updated_start = updated_start.replace(tzinfo=timezone.utc)
            if updated_end.tzinfo is None:
                updated_end = updated_end.replace(tzinfo=timezone.utc)
            
            # Validate time range
            if updated_start >= updated_end:
                raise BookingValidationError("Start time must be before end time")
            
            duration = updated_end - updated_start
            if duration.total_seconds() < 900:  # 15 minutes
                raise BookingValidationError("Booking duration must be at least 15 minutes")
            
            if duration.total_seconds() > 86400:  # 24 hours
                raise BookingValidationError("Booking duration cannot exceed 24 hours")
            
            # Check for conflicts (excluding current booking)
            conflicts = self.check_booking_conflicts(
                existing_booking.space_id,
                updated_start,
                updated_end,
                exclude_booking_id=booking_id
            )
            
            if conflicts:
                conflict_details = []
                for conflict in conflicts:
                    conflict_details.append(
                        f"Booking {conflict.id} from {conflict.start_time} to {conflict.end_time}"
                    )
                raise BookingConflictError(
                    f"Booking update conflicts detected: {'; '.join(conflict_details)}"
                )
        
        # Update the booking
        if booking_update.start_time:
            existing_booking.start_time = updated_start
        if booking_update.end_time:
            existing_booking.end_time = updated_end
        if booking_update.license_plate:
            existing_booking.license_plate = updated_license_plate
        
        self.db.commit()
        self.db.refresh(existing_booking)
        
        return existing_booking
    
    def get_booking_suggestions(
        self, 
        space_id: int, 
        preferred_start: datetime, 
        duration_minutes: int = 60
    ) -> List[dict]:
        """
        Get alternative booking suggestions when preferred time is not available
        
        Args:
            space_id: ID of the parking space
            preferred_start: Preferred start time
            duration_minutes: Desired booking duration in minutes
            
        Returns:
            List of alternative time slots
        """
        suggestions = []
        duration = timedelta(minutes=duration_minutes)
        
        # Check slots before and after preferred time
        for offset_hours in [-2, -1, 1, 2, 3, 4]:
            suggested_start = preferred_start + timedelta(hours=offset_hours)
            suggested_end = suggested_start + duration
            
            # Skip past times
            now = datetime.now(timezone.utc)
            if suggested_start < now:
                continue
            
            # Check if this slot is available
            conflicts = self.check_booking_conflicts(
                space_id, suggested_start, suggested_end
            )
            
            if not conflicts:
                suggestions.append({
                    'start_time': suggested_start,
                    'end_time': suggested_end,
                    'offset_hours': offset_hours
                })
        
        return suggestions[:5]  # Return top 5 suggestions
        
    def get_active_bookings_with_license_plates(
        self,
        reference_time: Optional[datetime] = None
    ) -> Dict[int, str]:
        """
        Get all currently active bookings with their license plates
        
        Args:
            reference_time: Time to check for active bookings (defaults to current time)
            
        Returns:
            Dictionary mapping space_id to license plate for all active bookings
        """
        if reference_time is None:
            reference_time = datetime.now(timezone.utc)
        
        # Ensure reference time is timezone-aware
        if reference_time.tzinfo is None:
            reference_time = reference_time.replace(tzinfo=timezone.utc)
            
        # Query for all active bookings that include the reference time
        print(f"Fetching active bookings at reference time: {reference_time}")
        active_bookings = self.db.query(models.Booking).filter(
            models.Booking.is_cancelled == False,
            models.Booking.start_time <= reference_time,
            models.Booking.end_time > reference_time
        ).all()
        
        print(f"Found {len(active_bookings)} active bookings")
        
        # Create a mapping of space_id to license plate
        space_to_license = {}
        for booking in active_bookings:
            print(f"Active booking: space_id={booking.space_id}, license_plate={booking.license_plate}")
            space_to_license[booking.space_id] = booking.license_plate
            
        print(f"Final space_to_license mapping: {space_to_license}")
        return space_to_license