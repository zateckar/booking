from datetime import datetime
from fastapi import APIRouter, Depends, File, UploadFile, HTTPException
from sqlalchemy.orm import Session
import shutil
import os
import requests
import uuid

from .. import models, schemas
from ..database import get_db
from ..security import get_current_admin_user, get_current_user

router = APIRouter(prefix="/api", tags=["parking-lots"])


@router.get("/parking-lots/", response_model=list[schemas.ParkingLot])
def read_parking_lots(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    parking_lots = db.query(models.ParkingLot).offset(skip).limit(limit).all()
    return parking_lots


@router.get("/parking-lots/{lot_id}", response_model=schemas.ParkingLot)
def read_parking_lot(
    lot_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_admin_user),
):
    db_parking_lot = db.query(models.ParkingLot).filter(models.ParkingLot.id == lot_id).first()
    if db_parking_lot is None:
        raise HTTPException(status_code=404, detail="Parking lot not found")
    return db_parking_lot


@router.get("/parking-lots/{lot_id}/spaces/", response_model=list[schemas.ParkingSpace])
def read_parking_spaces_for_lot(
    lot_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    spaces = db.query(models.ParkingSpace).filter(models.ParkingSpace.lot_id == lot_id).all()
    return spaces


@router.get(
    "/parking-lots/{lot_id}/spaces/availability",
    response_model=schemas.AvailabilityResponse,
)
def get_parking_space_availability(
    lot_id: int,
    start_time: datetime,
    end_time: datetime,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    booked_spaces = (
        db.query(models.Booking.space_id, models.Booking.license_plate)
        .join(models.ParkingSpace)
        .filter(
            models.ParkingSpace.lot_id == lot_id,
            models.Booking.is_cancelled == False,
            models.Booking.start_time < end_time,
            models.Booking.end_time > start_time,
        )
        .distinct()
        .all()
    )
    
    booked_space_ids = [space_id for (space_id, license_plate) in booked_spaces]
    space_license_plates = {space_id: license_plate for (space_id, license_plate) in booked_spaces}
    
    return {
        "booked_space_ids": booked_space_ids,
        "space_license_plates": space_license_plates
    }
