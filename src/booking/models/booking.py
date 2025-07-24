from sqlalchemy import Boolean, Column, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from .base import BaseModel, TimezoneAwareDateTime


class Booking(BaseModel):
    __tablename__ = "bookings"

    space_id = Column(Integer, ForeignKey("parking_spaces.id", ondelete="SET NULL"), nullable=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    start_time = Column(TimezoneAwareDateTime)
    end_time = Column(TimezoneAwareDateTime)
    license_plate = Column(String)
    is_cancelled = Column(Boolean, default=False)
    # Store deleted space info for historical purposes
    deleted_space_info = Column(String, nullable=True)  # JSON string with space details

    space = relationship("ParkingSpace")
    user = relationship("User", back_populates="bookings")
