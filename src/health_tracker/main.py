from fastapi import FastAPI, Depends, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from mangum import Mangum
from datetime import date, datetime, timezone
import os

from .database import SessionLocal
from . import models
from .schemas import (
    FoodEventIn,
    FoodEventOut,
    DailyTotalOut,
    NutritionFillIn,
    NutritionFillOut,
)
from .timeutil import to_london_date

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
handler = Mangum(app)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@app.on_event("startup")
def maybe_create_tables():
    # Keep migrations external by default. Opt-in for local/dev.
    if os.getenv("HEALTH_TRACKER_AUTO_MIGRATE", "0") in {"1", "true", "True"}:
        from .database import Base, engine
        Base.metadata.create_all(bind=engine)


@app.get("/health")
def health_check():
    return {"ok": True, "ts": datetime.now(timezone.utc).isoformat()}


@app.post("/food_events", response_model=FoodEventOut)
def create_food_event(event: FoodEventIn, db: Session = Depends(get_db)):
    now_utc = datetime.now(timezone.utc)

    obj = models.FoodEvent(ts=event.ts, raw_text=event.raw_text, calories=event.calories)

    cache = (
        db.query(models.NutritionCache)
        .filter_by(query_text=event.raw_text)
        .first()
    )
    if cache and cache.calories is not None:
        obj.calories = cache.calories
    else:
        # Seed cache for this raw_text if unknown
        db.add(
            models.NutritionCache(
                query_text=event.raw_text,
                calories=event.calories,
                created_at=now_utc,
            )
        )

    db.add(obj)

    d = to_london_date(event.ts)
    total = (
        db.query(models.DailyTotal)
        .filter(
            models.DailyTotal.date_local == d,
            models.DailyTotal.tz == "Europe/London",
        )
        .first()
    )
    if not total:
        total = models.DailyTotal(
            date_local=d,
            tz="Europe/London",
            calories=0.0,
            protein_g=0.0,
            carbs_g=0.0,
            fat_g=0.0,
            items_count=0,
        )
        db.add(total)

    total.calories = float(total.calories or 0.0) + float(obj.calories or 0.0)
    total.items_count = int(total.items_count or 0) + 1

    db.commit()
    db.refresh(obj)
    return obj


@app.get("/food_events")
def list_food_events(db: Session = Depends(get_db)):
    return db.query(models.FoodEvent).order_by(models.FoodEvent.ts.desc()).all()


@app.get("/daily_total/today", response_model=DailyTotalOut)
def get_today_total(db: Session = Depends(get_db)):
    d = to_london_date(datetime.now(timezone.utc))
    total = (
        db.query(models.DailyTotal)
        .filter(
            models.DailyTotal.date_local == d,
            models.DailyTotal.tz == "Europe/London",
        )
        .first()
    )
    return total or models.DailyTotal(date_local=d, tz="Europe/London")


@app.get("/daily_total/{iso_date}", response_model=DailyTotalOut)
def get_daily_total(iso_date: str, db: Session = Depends(get_db)):
    try:
        d = date.fromisoformat(iso_date)
    except ValueError:
        raise HTTPException(status_code=400, detail="iso_date must be YYYY-MM-DD")
    total = (
        db.query(models.DailyTotal)
        .filter(
            models.DailyTotal.date_local == d,
            models.DailyTotal.tz == "Europe/London",
        )
        .first()
    )
    return total or models.DailyTotal(date_local=d, tz="Europe/London")


@app.get("/nutrition_cache/{query}")
def get_cached(query: str, db: Session = Depends(get_db)):
    hit = (
        db.query(models.NutritionCache)
        .filter(models.NutritionCache.query_text == query)
        .first()
    )
    if not hit:
        return {"cached": False, "query_text": query}
    return {
        "cached": True,
        "query_text": hit.query_text,
        "calories": hit.calories,
        "protein_g": hit.protein_g,
        "carbs_g": hit.carbs_g,
        "fat_g": hit.fat_g,
        "fiber_g": hit.fiber_g,
    }


@app.post("/nutrition_lookup")
def create_lookup_placeholder(
    item: str = Query(..., min_length=1),
    db: Session = Depends(get_db),
):
    """Explicitly create a placeholder if missing. No side effects on GET."""
    now_utc = datetime.now(timezone.utc)

    hit = db.query(models.NutritionCache).filter_by(query_text=item).first()
    if hit:
        return {"created": False, "cached": True, "query_text": hit.query_text}

    placeholder = models.NutritionCache(
        query_text=item,
        calories=0.0,
        protein_g=0.0,
        carbs_g=0.0,
        fat_g=0.0,
        fiber_g=0.0,
        created_at=now_utc,
    )
    db.add(placeholder)
    db.commit()
    return {"created": True, "cached": False, "query_text": item}


def recalc_daily_total(db: Session, d: date):
    # sum calories from events; macros from cache if available
    events = db.query(models.FoodEvent).all()
    cals = prot = carbs = fat = fiber = items = 0
    for e in events:
        if to_london_date(e.ts) != d:
            continue
        cals += float(e.calories or 0)
        items += 1
        cache = db.query(models.NutritionCache).filter_by(query_text=e.raw_text).first()
        if cache:
            prot += float(cache.protein_g or 0)
            carbs += float(cache.carbs_g or 0)
            fat += float(cache.fat_g or 0)
            fiber += float(cache.fiber_g or 0)

    total = db.query(models.DailyTotal).filter(
        models.DailyTotal.date_local == d,
        models.DailyTotal.tz == "Europe/London"
    ).first()
    if not total:
        total = models.DailyTotal(date_local=d, tz="Europe/London")
        db.add(total)
    total.calories = cals
    total.protein_g = prot
    total.carbs_g = carbs
    total.fat_g = fat
    total.fiber_g = fiber
    total.items_count = items

@app.post("/nutrition_fill", response_model=NutritionFillOut)
def fill_cache(payload: NutritionFillIn, db: Session = Depends(get_db)):
    now_utc = datetime.now(timezone.utc)

    data = payload.model_dump()
    cache = db.query(models.NutritionCache).filter_by(query_text=data["item"]).first()
    if not cache:
        raise HTTPException(status_code=404, detail="Item not found in cache")

    # Partial update: only apply provided non-None fields except 'item'
    for key, value in data.items():
        if key == "item":
            continue
        if value is not None:
            setattr(cache, key, value)

    cache.created_at = now_utc
    db.commit()

    events = db.query(models.FoodEvent).filter_by(raw_text=cache.query_text).all()
    dates = {to_london_date(e.ts) for e in events}
    for d in dates:
        recalc_daily_total(db, d)
    db.commit()

    return NutritionFillOut(
        item=cache.query_text,
        calories=cache.calories,
        protein_g=cache.protein_g,
        carbs_g=cache.carbs_g,
        fat_g=cache.fat_g,
        fiber_g=cache.fiber_g,
    )
