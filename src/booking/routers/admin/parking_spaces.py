from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from ... import models, schemas
from ...database import get_db
from ...security import get_current_admin_user, get_current_user

router = APIRouter()


@router.get("/parking-lots/{lot_id}/spaces/", response_model=list[schemas.ParkingSpace])
def get_parking_spaces_for_lot(
    request: Request,
    lot_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_admin_user),
):
    """Get all parking spaces for a specific lot (admin endpoint)"""
    # Verify the parking lot exists
    db_lot = db.query(models.ParkingLot).filter(models.ParkingLot.id == lot_id).first()
    if db_lot is None:
        raise HTTPException(status_code=404, detail="Parking lot not found")
    
    spaces = db.query(models.ParkingSpace).filter(models.ParkingSpace.lot_id == lot_id).all()
    return spaces


@router.post("/parking-lots/{lot_id}/spaces/", response_model=schemas.ParkingSpace)
def create_parking_space_for_lot(
    request: Request,
    lot_id: int,
    space: schemas.ParkingSpaceCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_admin_user),
):
    db_space = models.ParkingSpace(**space.model_dump(), lot_id=lot_id)
    db.add(db_space)
    db.commit()
    db.refresh(db_space)
    return db_space




@router.put("/parking-lots/{lot_id}/spaces/", response_model=list[schemas.ParkingSpace])
def update_parking_spaces(
    request: Request,
    lot_id: int,
    spaces: list[schemas.ParkingSpaceBulkUpdate],
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_admin_user),
):
    updated_spaces = []
    for space_update in spaces:
        db_space = (
            db.query(models.ParkingSpace)
            .filter(models.ParkingSpace.id == space_update.id)
            .first()
        )
        if db_space:
            space_data = space_update.model_dump(exclude_unset=True)
            for key, value in space_data.items():
                setattr(db_space, key, value)
            db.add(db_space)
            updated_spaces.append(db_space)
    db.commit()
    for db_space in updated_spaces:
        db.refresh(db_space)
    return updated_spaces


@router.put("/parking-lots/{lot_id}/spaces/{space_id}", response_model=schemas.ParkingSpace)
def update_parking_space(
    request: Request,
    lot_id: int,
    space_id: int,
    space: schemas.ParkingSpaceUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_admin_user),
):
    db_space = db.query(models.ParkingSpace).filter(models.ParkingSpace.id == space_id).first()
    if db_space is None:
        raise HTTPException(status_code=404, detail="Parking space not found")
    space_data = space.model_dump(exclude_unset=True)
    for key, value in space_data.items():
        setattr(db_space, key, value)
    db.add(db_space)
    db.commit()
    db.refresh(db_space)
    return db_space


@router.delete("/parking-lots/{lot_id}/spaces/{space_id}")
def delete_parking_space(
    request: Request,
    lot_id: int,
    space_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_admin_user),
):
    # First verify the space exists and belongs to the specified lot
    db_space = (
        db.query(models.ParkingSpace)
        .filter(
            models.ParkingSpace.id == space_id,
            models.ParkingSpace.lot_id == lot_id
        )
        .first()
    )
    
    if db_space is None:
        raise HTTPException(status_code=404, detail="Parking space not found")
    
    # Store space info before deletion for response
    space_info = {
        "id": db_space.id,
        "space_number": db_space.space_number,
        "lot_id": db_space.lot_id
    }
    
    # Delete the space
    db.delete(db_space)
    db.commit()
    
    return {
        "message": f"Parking space '{space_info['space_number']}' deleted successfully",
        "deleted_space_id": space_info["id"]
    }
