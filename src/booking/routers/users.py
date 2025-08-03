from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
import logging

from .. import models, schemas
from ..database import get_db
from ..security import create_access_token, get_current_user, get_password_hash, verify_password
from ..logging_config import get_logger, log_with_context

logger = get_logger("routers.users")

router = APIRouter()


@router.post("/api/users/", response_model=schemas.User)
def create_user(user: schemas.UserCreate, db: Session = Depends(get_db)):
    logger.info(f"Attempting to create user with email: {user.email}")
    
    db_user = db.query(models.User).filter(models.User.email == user.email).first()
    if db_user:
        logger.warning(f"User creation failed - email already registered: {user.email}")
        raise HTTPException(status_code=400, detail="Email already registered")
    
    hashed_password = get_password_hash(user.password)
    db_user = models.User(email=user.email, hashed_password=hashed_password)
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    
    logger.info(f"Successfully created user: {user.email} (ID: {db_user.id})")
    return db_user


@router.get("/api/users/", response_model=list[schemas.User])
def read_users(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    users = db.query(models.User).offset(skip).limit(limit).all()
    return users


@router.get("/api/users/me", response_model=schemas.User)
def read_users_me(
    request: Request,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
    include_parking_lots: bool = False,
):
    if include_parking_lots:
        current_user.parking_lots = db.query(models.ParkingLot).all()
    return current_user


@router.get("/api/users/me/license-plates", response_model=list[str])
def read_user_license_plates(request: Request, current_user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    license_plates = (
        db.query(models.Booking.license_plate)
        .filter(models.Booking.user_id == current_user.id)
        .distinct()
        .all()
    )
    return [lp for lp, in license_plates]


@router.get("/api/users/{user_id}", response_model=schemas.User)
def read_user(user_id: int, db: Session = Depends(get_db)):
    db_user = db.query(models.User).filter(models.User.id == user_id).first()
    if db_user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return db_user


@router.post("/api/token")
def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    logger.info(f"Login attempt for user: {form_data.username}")
    
    user = db.query(models.User).filter(models.User.email == form_data.username).first()
    if not user or not verify_password(form_data.password, user.hashed_password):
        logger.warning(f"Failed login attempt for user: {form_data.username}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token = create_access_token(data={"sub": user.email, "is_admin": user.is_admin})
    
    log_with_context(
        logger, logging.INFO,
        f"Successful login for user: {user.email}",
        user_id=user.id,
        extra_data={"is_admin": user.is_admin}
    )
    
    return {"access_token": access_token, "token_type": "bearer"}
