from sqlalchemy import Column, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from .base import BaseModel


class ParkingLot(BaseModel):
    __tablename__ = "parking_lots"

    name = Column(String, index=True)
    image = Column(String)

    spaces = relationship("ParkingSpace", back_populates="parking_lot", cascade="all, delete-orphan")


class ParkingSpace(BaseModel):
    __tablename__ = "parking_spaces"

    lot_id = Column(Integer, ForeignKey("parking_lots.id", ondelete="CASCADE"))
    space_number = Column(String)
    position_x = Column(Integer)
    position_y = Column(Integer)
    width = Column(Integer)
    height = Column(Integer)
    color = Column(String)

    parking_lot = relationship("ParkingLot", back_populates="spaces")
