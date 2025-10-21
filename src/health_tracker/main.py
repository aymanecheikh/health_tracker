from fastapi import FastAPI
from pydantic import BaseModel
from datetime import datetime
from .database import SessionLocal, Base, engine
from . import models

app = FastAPI()
Base.metadata.create_all(bind=engine)

class FoodEventIn(BaseModel):
    ts: datetime
    raw_text: str
    calories: float


@app.get("/health")
def health_check():
    return {"ok": True}

@app.post("/food_events")
def create_food_event(event: FoodEventIn):
    db = SessionLocal()
    obj = models.FoodEvent(
        ts=event.ts,
        raw_text=event.raw_text,
        calories=event.calories
    )
    db.add(obj)
    db.commit()
    db.refresh(obj)
    db.close()
    return obj