from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session
from mangum import Mangum
from datetime import date, datetime, timezone
from .database import SessionLocal, Base, engine
from . import models
from .schemas import FoodEventIn, FoodEventOut, DailyTotalOut, NutritionFillIn
from .timeutil import to_london_date


app = FastAPI()
handler = Mangum(app)
Base.metadata.create_all(bind=engine)
now_utc = datetime.now(timezone.utc)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@app.get("/health")
def health_check():
    return {"ok": True}

@app.post("/food_events", response_model=FoodEventOut)
def create_food_event(event: FoodEventIn, db: Session = Depends(get_db)):
    obj = models.FoodEvent(
        ts=event.ts,
        raw_text=event.raw_text,
        calories=event.calories
    )
    cache = db.query(models.NutritionCache).filter_by(
        query_text=event.raw_text
    ).first()
    if cache:
        obj.calories = cache.calories
    else:
        cache = models.NutritionCache(
            query_text=event.raw_text,
            calories=event.calories,
            created_at=now_utc
        )
        db.add(cache)
    db.add(obj)
    d = to_london_date(event.ts)
    total = db.query(models.DailyTotal).filter(
        models.DailyTotal.date_local == d,
        models.DailyTotal.tz == "Europe/London"
    ).first()
    if not total:
        total = models.DailyTotal(
            date_local=d,
            tz="Europe/London",
            calories=0.0,
            protein_g=0.0,
            carbs_g=0.0,
            fat_g=0.0,
            items_count=0
        )
        db.add(total)
    total.calories = (total.calories or 0.0) + (obj.calories or 0.0)
    total.items_count = (total.items_count or 0) + 1
    db.commit()
    db.refresh(obj)
    return obj

@app.get("/food_events")
def list_food_events(db: Session = Depends(get_db)):
    return (
        db.query(models.FoodEvent).order_by(models.FoodEvent.ts.desc()).all()
        )

@app.get("/daily_total/today", response_model=DailyTotalOut)
def get_today_total(db: Session = Depends(get_db)):
    d = to_london_date(datetime.now())
    total = db.query(models.DailyTotal).filter(
        models.DailyTotal.date_local == d,
        models.DailyTotal.tz == "Europe/London"
    ).first()
    return total or models.DailyTotal(
        date_local=d,
        tz="Europe/London")

@app.get("/daily_total/{iso_date}", response_model=DailyTotalOut)
def get_daily_total(iso_date: str, db: Session = Depends(get_db)):
    d = date.fromisoformat(iso_date)
    total = db.query(models.DailyTotal).filter(
        models.DailyTotal.date_local == d,
        models.DailyTotal.tz == "Europe/London"
    ).first()
    return total or models.DailyTotal(
        date_local=d,
        tz="Europe/London")

@app.get("/nutrition_cache/{query}")
def get_cached(query: str, db: Session = Depends(get_db)):
    hit = db.query(models.NutritionCache).filter(
        models.NutritionCache.query_text == query
    ).first()
    return hit or {"cached": False}

@app.post("/nutrition_fill", response_model=NutritionFillIn)
def fill_cache(payload: NutritionFillIn, db: Session = Depends(get_db)):
    data = payload.model_dump()
    cache = db.query(models.NutritionCache).filter_by(
        query_text=data["item"]
    ).first()
    if not cache:
        raise HTTPException(status_code=404, detail="Item not found in cache")
    for key, value in data.items():
        if key != "item":
            setattr(cache, key, value)
    cache.created_at = now_utc
    db.commit()
    return {
        "item": cache.query_text,
        "calories": cache.calories,
        "protein_g": cache.protein_g,
        "carbs_g": cache.carbs_g,
        "fat_g": cache.fat_g,
        "fiber_g": cache.fiber_g
    }
