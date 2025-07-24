from sqlalchemy import Boolean, Column, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from .base import BaseModel, TimezoneAwareDateTime


class User(BaseModel):
    __tablename__ = "users"

    email = Column(String, unique=True, index=True)
    hashed_password = Column(String)
    is_admin = Column(Boolean, default=False)

    bookings = relationship("Booking", back_populates="user")
    profile = relationship("UserProfile", back_populates="user", uselist=False)


class UserProfile(BaseModel):
    __tablename__ = "user_profiles"

    user_id = Column(Integer, ForeignKey("users.id"), unique=True, index=True)
    profile_data = Column(String)  # JSON field for dynamic key-value storage
    last_oidc_update = Column(TimezoneAwareDateTime)

    user = relationship("User", back_populates="profile")
