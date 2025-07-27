from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy.orm import Session, joinedload
from typing import List, Optional
from datetime import datetime, date
import io
import pandas as pd

from ... import models, schemas
from ...database import get_db

router = APIRouter()


@router.get("/bookings", response_model=List[schemas.BookingAdmin])
def get_all_bookings(
    db: Session = Depends(get_db),
    user_id: Optional[int] = Query(None, description="Filter by user ID"),
    parking_lot_id: Optional[int] = Query(None, description="Filter by parking lot ID"),
    start_date: Optional[date] = Query(None, description="Filter bookings from this date"),
    end_date: Optional[date] = Query(None, description="Filter bookings until this date"),
    include_cancelled: bool = Query(True, description="Include cancelled bookings"),
    limit: Optional[int] = Query(None, description="Limit number of results"),
    offset: Optional[int] = Query(0, description="Offset for pagination")
):
    """Get all bookings with optional filtering"""
    query = db.query(models.Booking).options(
        joinedload(models.Booking.user),
        joinedload(models.Booking.space).joinedload(models.ParkingSpace.parking_lot)
    )
    
    # Apply filters
    if user_id:
        query = query.filter(models.Booking.user_id == user_id)
    
    if parking_lot_id:
        query = query.join(models.ParkingSpace).filter(
            models.ParkingSpace.lot_id == parking_lot_id
        )
    
    if start_date:
        query = query.filter(models.Booking.start_time >= start_date)
    
    if end_date:
        # Add one day to include bookings on the end date
        end_datetime = datetime.combine(end_date, datetime.max.time())
        query = query.filter(models.Booking.end_time <= end_datetime)
    
    if not include_cancelled:
        query = query.filter(models.Booking.is_cancelled == False)
    
    # Order by start time descending (newest first)
    query = query.order_by(models.Booking.start_time.desc())
    
    # Apply pagination
    if offset:
        query = query.offset(offset)
    if limit:
        query = query.limit(limit)
    
    return query.all()


@router.get("/bookings/count")
def get_bookings_count(
    db: Session = Depends(get_db),
    user_id: Optional[int] = Query(None),
    parking_lot_id: Optional[int] = Query(None),
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    include_cancelled: bool = Query(True)
):
    """Get count of bookings matching filters"""
    query = db.query(models.Booking)
    
    # Apply same filters as get_all_bookings
    if user_id:
        query = query.filter(models.Booking.user_id == user_id)
    
    if parking_lot_id:
        query = query.join(models.ParkingSpace).filter(
            models.ParkingSpace.lot_id == parking_lot_id
        )
    
    if start_date:
        query = query.filter(models.Booking.start_time >= start_date)
    
    if end_date:
        end_datetime = datetime.combine(end_date, datetime.max.time())
        query = query.filter(models.Booking.end_time <= end_datetime)
    
    if not include_cancelled:
        query = query.filter(models.Booking.is_cancelled == False)
    
    return {"count": query.count()}


@router.delete("/bookings/{booking_id}")
def delete_booking(booking_id: int, db: Session = Depends(get_db)):
    """Delete a specific booking"""
    booking = db.query(models.Booking).filter(models.Booking.id == booking_id).first()
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")
    
    db.delete(booking)
    db.commit()
    return {"message": "Booking deleted successfully", "booking_id": booking_id}


@router.get("/bookings/export")
def export_bookings_excel(
    db: Session = Depends(get_db),
    user_id: Optional[int] = Query(None),
    parking_lot_id: Optional[int] = Query(None),
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    include_cancelled: bool = Query(True)
):
    """Export filtered bookings to Excel file"""
    # Get bookings with the same filters (without pagination)
    query = db.query(models.Booking).options(
        joinedload(models.Booking.user),
        joinedload(models.Booking.space).joinedload(models.ParkingSpace.parking_lot)
    )
    
    # Apply filters
    if user_id:
        query = query.filter(models.Booking.user_id == user_id)
    
    if parking_lot_id:
        query = query.join(models.ParkingSpace).filter(
            models.ParkingSpace.lot_id == parking_lot_id
        )
    
    if start_date:
        query = query.filter(models.Booking.start_time >= start_date)
    
    if end_date:
        end_datetime = datetime.combine(end_date, datetime.max.time())
        query = query.filter(models.Booking.end_time <= end_datetime)
    
    if not include_cancelled:
        query = query.filter(models.Booking.is_cancelled == False)
    
    # Order by start time
    bookings = query.order_by(models.Booking.start_time.desc()).all()
    
    # Prepare data for Excel
    data = []
    for booking in bookings:
        row = {
            'Booking ID': booking.id,
            'User Email': booking.user.email if booking.user else 'N/A',
            'User ID': booking.user_id,
            'Parking Lot': booking.space.parking_lot.name if booking.space and booking.space.parking_lot else booking.deleted_space_info or 'N/A',
            'Space Number': booking.space.space_number if booking.space else 'Deleted Space',
            'Start Time': booking.start_time.isoformat() if booking.start_time else '',
            'End Time': booking.end_time.isoformat() if booking.end_time else '',
            'License Plate': booking.license_plate or '',
            'Status': 'Cancelled' if booking.is_cancelled else 'Active',
            'Created': booking.created_at.isoformat() if booking.created_at else '',
            'Updated': booking.updated_at.isoformat() if booking.updated_at else ''
        }
        data.append(row)
    
    # Create Excel file
    df = pd.DataFrame(data)
    
    # Create Excel file in memory
    excel_buffer = io.BytesIO()
    with pd.ExcelWriter(excel_buffer, engine='openpyxl') as writer:
        df.to_excel(writer, sheet_name='Bookings', index=False)
        
        # Auto-adjust column widths
        worksheet = writer.sheets['Bookings']
        for column in worksheet.columns:
            max_length = 0
            column_letter = column[0].column_letter
            for cell in column:
                try:
                    if len(str(cell.value)) > max_length:
                        max_length = len(str(cell.value))
                except:
                    pass
            adjusted_width = min(max_length + 2, 50)
            worksheet.column_dimensions[column_letter].width = adjusted_width
    
    excel_buffer.seek(0)
    
    # Generate filename with current timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"bookings_export_{timestamp}.xlsx"
    
    # Return Excel file
    return Response(
        content=excel_buffer.getvalue(),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )


@router.get("/bookings/users")
def get_users_with_bookings(db: Session = Depends(get_db)):
    """Get list of users who have bookings"""
    users = db.query(models.User).join(models.Booking).distinct().all()
    return [{"id": user.id, "email": user.email} for user in users]


@router.get("/bookings/parking-lots")
def get_parking_lots_with_bookings(db: Session = Depends(get_db)):
    """Get list of parking lots that have bookings"""
    lots = (db.query(models.ParkingLot)
            .join(models.ParkingSpace)
            .join(models.Booking)
            .distinct()
            .all())
    return [{"id": lot.id, "name": lot.name} for lot in lots]
