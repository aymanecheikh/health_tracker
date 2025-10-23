from pydantic import BaseModel
from datetime import datetime, date

class FoodEventIn(BaseModel):
    ts: datetime
    raw_text: str
    calories: float

class FoodEventOut(BaseModel):
    id: int
    ts: datetime
    class Config: from_attributes = True

class DailyTotalOut(BaseModel):
    date_local: date
    tz: str
    calories: float
    protein_g: float
    carbs_g: float
    fat_g: float
    fiber_g: float
    items_count: int
    class Config: from_attributes = True

class NutritionFillIn(BaseModel):
    item: str
    calories: float
    protein_g: float = 0.0
    carbs_g: float = 0.0
    fat_g: float = 0.0
    fiber_g: float = 0.0