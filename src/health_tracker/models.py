from .database import Base
from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, DateTime, Date


class FoodEvent(Base):
    __tablename__ = "food_events"

    id = Column(Integer, primary_key=True, index=True)
    ts = Column(DateTime, nullable=False)
    raw_text = Column(String, nullable=False)
    calories = Column(Float, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

class DailyTotal(Base):
    __tablename__ = "daily_totals"

    id = Column(Integer, primary_key=True, index=True)
    date_local = Column(Date, nullable=False, index=True)
    tz = Column(String, nullable=False, default="Europe/London")
    calories = Column(Float, nullable=False, default=0.0)
    protein_g = Column(Float, nullable=False, default=0.0)
    carbs_g = Column(Float, nullable=False, default=0.0)
    fat_g = Column(Float, nullable=False, default=0.0)
    fiber_g = Column(Float, nullable=False, default=0.0)
    items_count = Column(Integer, nullable=False, default=0)
    closed_at = Column(DateTime, nullable=True)