from fastapi import APIRouter, Depends, File, UploadFile, HTTPException, Form, Request
from sqlalchemy.orm import Session
import shutil
import os
import requests
import uuid
import json
from datetime import datetime, timezone

from ... import models, schemas
from ...database import get_db
from ...security import get_current_admin_user

router = APIRouter(prefix="/parking-lots", tags=["admin-parking-lots"])


@router.get("/")
def get_parking_lots(
    request: Request,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_admin_user),
):
    """Get all parking lots with space count for admin interface"""
    parking_lots = db.query(models.ParkingLot).all()
    
    # Add space count to each parking lot
    result = []
    for lot in parking_lots:
        space_count = db.query(models.ParkingSpace).filter(models.ParkingSpace.lot_id == lot.id).count()
        lot_dict = {
            "id": lot.id,
            "name": lot.name,
            "image": lot.image,
            "space_count": space_count
        }
        result.append(lot_dict)
    
    return result


@router.post("/", response_model=schemas.ParkingLot)
def create_parking_lot(
    request: Request,
    name: str = Form(...),
    image: str | None = Form(None),
    upload_image: UploadFile = File(None),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_admin_user),
):
    image_dir = "static/images/parking_lots"
    if not os.path.exists(image_dir):
        os.makedirs(image_dir)

    image_url = None
    if upload_image and upload_image.filename:
        file_extension = os.path.splitext(upload_image.filename)[1]
        filename = f"{uuid.uuid4()}{file_extension}"
        image_path = os.path.join(image_dir, filename)
        with open(image_path, "wb") as buffer:
            shutil.copyfileobj(upload_image.file, buffer)
        image_url = f"/{image_path}"
    elif image:
        try:
            response = requests.get(image, stream=True)
            response.raise_for_status()
            file_extension = os.path.splitext(image.split("/")[-1])[1].split("?")[0] or ".jpg"
            filename = f"{uuid.uuid4()}{file_extension}"
            image_path = os.path.join(image_dir, filename)
            with open(image_path, "wb") as buffer:
                for chunk in response.iter_content(chunk_size=8192):
                    buffer.write(chunk)
            image_url = f"/{image_path}"
        except requests.exceptions.RequestException as e:
            raise HTTPException(status_code=400, detail=f"Could not download image: {e}")

    if not image_url:
        raise HTTPException(status_code=400, detail="Either image URL or image file must be provided")

    db_parking_lot = models.ParkingLot(name=name, image=image_url)
    db.add(db_parking_lot)
    db.commit()
    db.refresh(db_parking_lot)
    return db_parking_lot


@router.put("/{lot_id}", response_model=schemas.ParkingLot)
def update_parking_lot(
    request: Request,
    lot_id: int,
    name: str = Form(...),
    image: str | None = Form(None),
    upload_image: UploadFile = File(None),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_admin_user),
):
    db_parking_lot = db.query(models.ParkingLot).filter(models.ParkingLot.id == lot_id).first()
    if db_parking_lot is None:
        raise HTTPException(status_code=404, detail="Parking lot not found")

    db_parking_lot.name = name

    if upload_image and upload_image.filename:
        image_dir = "static/images/parking_lots"
        if not os.path.exists(image_dir):
            os.makedirs(image_dir)
        
        file_extension = os.path.splitext(upload_image.filename)[1]
        filename = f"{uuid.uuid4()}{file_extension}"
        image_path = os.path.join(image_dir, filename)
        with open(image_path, "wb") as buffer:
            shutil.copyfileobj(upload_image.file, buffer)
        db_parking_lot.image = f"/{image_path}"
    elif image:
        db_parking_lot.image = image

    db.commit()
    db.refresh(db_parking_lot)
    return db_parking_lot


@router.delete("/{lot_id}")
def delete_parking_lot(
    request: Request,
    lot_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_admin_user),
):
    import json
    
    db_parking_lot = db.query(models.ParkingLot).filter(models.ParkingLot.id == lot_id).first()
    if db_parking_lot is None:
        raise HTTPException(status_code=404, detail="Parking lot not found")
    
    # Check for associated spaces and bookings
    spaces = db.query(models.ParkingSpace).filter(models.ParkingSpace.lot_id == lot_id).all()
    space_count = len(spaces)
    
    # Count bookings that will be affected
    booking_count = 0
    if spaces:
        space_ids = [space.id for space in spaces]
        
        # Store space information in related bookings before deletion
        for space in spaces:
            space_info = {
                "space_id": space.id,
                "space_number": space.space_number,
                "lot_id": space.lot_id,
                "lot_name": db_parking_lot.name,
                "deletion_date": datetime.now(timezone.utc).isoformat()
            }
            space_info_json = json.dumps(space_info)
            
            # Update bookings to store space info before the space is deleted
            bookings_to_update = db.query(models.Booking).filter(
                models.Booking.space_id == space.id,
                models.Booking.deleted_space_info.is_(None)  # Only update if not already set
            ).all()
            
            for booking in bookings_to_update:
                booking.deleted_space_info = space_info_json
                
        booking_count = db.query(models.Booking).filter(
            models.Booking.space_id.in_(space_ids)
        ).count()
    
    # Store parking lot data before deletion
    parking_lot_data = {
        "id": db_parking_lot.id,
        "name": db_parking_lot.name,
        "image": db_parking_lot.image
    }
    
    # Delete associated image file
    if db_parking_lot.image and os.path.exists(db_parking_lot.image.lstrip('/')):
        os.remove(db_parking_lot.image.lstrip('/'))

    # Delete the parking lot (this will cascade to delete associated spaces, 
    # but bookings will have space_id set to NULL while preserving deleted_space_info)
    db.delete(db_parking_lot)
    db.commit()
    
    return {
        "message": "Parking lot deleted successfully", 
        "parking_lot": parking_lot_data,
        "deleted_spaces": space_count,
        "preserved_bookings": booking_count
    }
