from sqlalchemy import Column, Integer, String, Float, DateTime
from .database import Base


class FoodEvent(Base):
    __tablename__ = "food_events"

    id = Column(Integer, primary_key=True, index=True)
    ts = Column(DateTime, nullable=False)
    raw_text = Column(String, nullable=False)
    calories = Column(Float, nullable=False)