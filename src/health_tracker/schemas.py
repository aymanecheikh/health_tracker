from datetime import datetime, date
from typing import Optional
from pydantic import BaseModel, Field, ConfigDict


class FoodEventIn(BaseModel):
    ts: datetime
    raw_text: str
    calories: float = Field(ge=0)


class FoodEventOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    ts: datetime
    raw_text: str
    calories: float


class DailyTotalOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    date_local: date
    tz: str = "Europe/London"
    calories: float = 0.0
    protein_g: float = 0.0
    carbs_g: float = 0.0
    fat_g: float = 0.0
    fiber_g: float = 0.0
    items_count: int = 0


class NutritionFillIn(BaseModel):
    # Partial update: only send fields you want to change
    item: str
    calories: Optional[float] = Field(default=None, ge=0)
    protein_g: Optional[float] = Field(default=None, ge=0)
    carbs_g: Optional[float] = Field(default=None, ge=0)
    fat_g: Optional[float] = Field(default=None, ge=0)
    fiber_g: Optional[float] = Field(default=None, ge=0)


class NutritionFillOut(BaseModel):
    item: str
    calories: float
    protein_g: float
    carbs_g: float
    fat_g: float
    fiber_g: float
