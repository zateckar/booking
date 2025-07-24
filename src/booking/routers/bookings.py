from datetime import date
from typing import Optional
import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, joinedload

from .. import models, schemas
from ..database import get_db
from ..security import get_current_admin_user, get_current_user
from ..services import BookingService, BookingConflictError, BookingValidationError
from ..timezone_service import TimezoneService
from ..logging_config import get_logger, log_with_context

logger = get_logger("routers.bookings")

router = APIRouter()


@router.post("/api/bookings/", response_model=schemas.BookingRead)
def create_booking(
    booking: schemas.BookingCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    log_with_context(
        logger, logging.INFO, 
        f"Creating booking for space {booking.space_id} from {booking.start_time} to {booking.end_time}",
        user_id=current_user.id,
        extra_data={"space_id": booking.space_id, "license_plate": booking.license_plate}
    )
    
    booking_service = BookingService(db)
    try:
        db_booking = booking_service.create_booking_with_validation(booking, current_user.id)
        
        log_with_context(
            logger, logging.INFO,
            f"Successfully created booking {db_booking.id} for user {current_user.email}",
            user_id=current_user.id,
            extra_data={"booking_id": db_booking.id}
        )
        
        return db_booking
    except BookingConflictError as e:
        log_with_context(
            logger, logging.WARNING,
            f"Booking conflict for user {current_user.email}: {str(e)}",
            user_id=current_user.id,
            extra_data={"space_id": booking.space_id, "conflict_reason": str(e)}
        )
        # Get alternative suggestions
        suggestions = booking_service.get_booking_suggestions(
            booking.space_id, 
            booking.start_time,
            int((booking.end_time - booking.start_time).total_seconds() / 60)
        )
        
        suggestion_text = ""
        if suggestions:
            suggestion_text = " Alternative times available: " + ", ".join([
                f"{s['start_time'].strftime('%H:%M')} ({s['offset_hours']:+d}h)"
                for s in suggestions[:3]
            ])
        
        raise HTTPException(
            status_code=409,
            detail=f"Booking conflict: {str(e)}.{suggestion_text}"
        )
    except BookingValidationError as e:
        log_with_context(
            logger, logging.WARNING,
            f"Booking validation error for user {current_user.email}: {str(e)}",
            user_id=current_user.id,
            extra_data={"space_id": booking.space_id, "validation_error": str(e)}
        )
        raise HTTPException(
            status_code=400,
            detail=f"Booking validation failed: {str(e)}"
        )


@router.get("/api/bookings/", response_model=list[schemas.BookingRead])
def read_bookings(
    db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)
):
    logger.debug(f"Fetching bookings for user {current_user.email}")
    
    bookings = (
        db.query(models.Booking)
        .options(joinedload(models.Booking.space).joinedload(models.ParkingSpace.parking_lot))
        .filter(models.Booking.user_id == current_user.id)
        .all()
    )
    return bookings


@router.get("/api/bookings/all", response_model=list[schemas.BookingRead])
def read_all_bookings(
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_admin_user),
):
    query = db.query(models.Booking).options(
        joinedload(models.Booking.user),
        joinedload(models.Booking.space).joinedload(models.ParkingSpace.parking_lot),
    )
    if start_date:
        query = query.filter(models.Booking.start_time >= start_date)
    if end_date:
        query = query.filter(models.Booking.end_time <= end_date)

    bookings = query.all()
    return bookings


@router.put("/api/bookings/{booking_id}", response_model=schemas.BookingRead)
def update_booking(
    booking_id: int,
    booking_update: schemas.BookingUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    booking_service = BookingService(db)
    try:
        updated_booking = booking_service.update_booking_with_validation(
            booking_id, booking_update, current_user.id
        )
        return updated_booking
    except BookingConflictError as e:
        # Get alternative suggestions if time was being updated
        if booking_update.start_time or booking_update.end_time:
            existing_booking = db.query(models.Booking).filter(
                models.Booking.id == booking_id
            ).first()
            if existing_booking:
                start_time = booking_update.start_time or existing_booking.start_time
                end_time = booking_update.end_time or existing_booking.end_time
                duration_minutes = int((end_time - start_time).total_seconds() / 60)
                
                suggestions = booking_service.get_booking_suggestions(
                    existing_booking.space_id, 
                    start_time,
                    duration_minutes
                )
                
                suggestion_text = ""
                if suggestions:
                    suggestion_text = " Alternative times available: " + ", ".join([
                        f"{s['start_time'].strftime('%H:%M')} ({s['offset_hours']:+d}h)"
                        for s in suggestions[:3]
                    ])
                
                raise HTTPException(
                    status_code=409,
                    detail=f"Booking update conflict: {str(e)}.{suggestion_text}"
                )
        
        raise HTTPException(
            status_code=409,
            detail=f"Booking update conflict: {str(e)}"
        )
    except BookingValidationError as e:
        raise HTTPException(
            status_code=400,
            detail=f"Booking update validation failed: {str(e)}"
        )


@router.put("/api/bookings/{booking_id}/cancel", response_model=schemas.Booking)
def cancel_booking(
    booking_id: int, 
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    # Enhanced cancellation with user authorization
    booking_service = BookingService(db)
    
    db_booking = db.query(models.Booking).filter(models.Booking.id == booking_id).first()
    if db_booking is None:
        raise HTTPException(status_code=404, detail="Booking not found")
    
    # Check if user owns the booking or is admin
    if db_booking.user_id != current_user.id and not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Not authorized to cancel this booking")
    
    if db_booking.is_cancelled:
        raise HTTPException(status_code=400, detail="Booking is already cancelled")
    
    db_booking.is_cancelled = True
    db.add(db_booking)
    db.commit()
    db.refresh(db_booking)
    return db_booking


@router.get("/api/bookings/suggestions")
def get_booking_suggestions(
    space_id: int,
    start_time: str,  # ISO format datetime string
    duration_minutes: int = 60,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Get alternative booking time suggestions when preferred time is not available"""
    from datetime import datetime
    
    try:
        # Parse the datetime string
        preferred_start = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
        
        booking_service = BookingService(db)
        timezone_service = TimezoneService(db)
        suggestions = booking_service.get_booking_suggestions(
            space_id, preferred_start, duration_minutes
        )
        
        # Format suggestions with local timezone
        formatted_suggestions = []
        for s in suggestions:
            formatted_suggestions.append({
                "start_time": s["start_time"].isoformat(),
                "end_time": s["end_time"].isoformat(),
                "start_time_local": timezone_service.format_datetime_local(s["start_time"], "%H:%M"),
                "offset_hours": s["offset_hours"]
            })
        
        return {
            "suggestions": formatted_suggestions,
            "timezone": timezone_service.get_system_timezone()
        }
    except ValueError as e:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid datetime format: {str(e)}"
        )


@router.get("/api/bookings/timezone")
def get_booking_timezone(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Get the current system timezone for booking display"""
    timezone_service = TimezoneService(db)
    return {
        "timezone": timezone_service.get_system_timezone(),
        "timezone_display": timezone_service.get_system_timezone().replace('_', ' ')
    }


@router.get("/api/bookings/active-spaces")
def get_active_spaces_with_license_plates(
    reference_time: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """
    Get all currently occupied parking spaces with their license plates
    
    This endpoint returns a mapping of space_id to license_plate for all spaces
    that are currently occupied (or occupied at the specified reference time).
    This information can be used to display license plate labels on the parking lot map.
    """
    from datetime import datetime
    
    try:
        # Parse the reference time if provided, otherwise use current time
        ref_time = None
        if reference_time:
            ref_time = datetime.fromisoformat(reference_time.replace('Z', '+00:00'))
        
        booking_service = BookingService(db)
        space_license_map = booking_service.get_active_bookings_with_license_plates(ref_time)
        
        # Debug print
        print(f"Active bookings with license plates: {space_license_map}")
        
        result = {
            "occupied_spaces": [
                {
                    "space_id": space_id,
                    "license_plate": license_plate
                }
                for space_id, license_plate in space_license_map.items()
            ]
        }
        
        # Debug print
        print(f"Response: {result}")
        
        return result
    except ValueError as e:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid datetime format: {str(e)}"
        )
