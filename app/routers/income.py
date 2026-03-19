from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.database import get_db
from app.models import Income
from app.schemas import IncomeCreate, IncomeOut
from typing import List

router = APIRouter(prefix="/income", tags=["Income"])


@router.post("/", response_model=IncomeOut)
def add_income(income: IncomeCreate, db: Session = Depends(get_db)):
    new_income = Income(
        date=income.date,
        amount=income.amount,
        source=income.source,
        note=income.note
    )
    db.add(new_income)
    db.commit()
    db.refresh(new_income)
    return new_income


@router.get("/", response_model=List[IncomeOut])
def get_income(db: Session = Depends(get_db)):
    return db.query(Income).order_by(Income.id.desc()).all()


@router.delete("/{income_id}")
def delete_income(income_id: int, db: Session = Depends(get_db)):
    income = db.query(Income).filter(Income.id == income_id).first()
    if not income:
        raise HTTPException(status_code=404, detail="Income not found")
    db.delete(income)
    db.commit()
    return {"message": "Income deleted successfully"}


@router.get("/summary/monthly")
def income_monthly_summary(db: Session = Depends(get_db)):
    result = db.execute(text(
        "SELECT strftime('%Y-%m', date) as month, "
        "SUM(amount) as total_income, "
        "COUNT(*) as total_entries "
        "FROM income "
        "GROUP BY month "
        "ORDER BY month DESC"
    )).fetchall()
    return [
        {
            "month": row[0],
            "total_income": row[1],
            "total_entries": row[2]
        }
        for row in result
    ]


@router.get("/summary/sources")
def income_by_source(db: Session = Depends(get_db)):
    result = db.execute(text(
        "SELECT source, "
        "SUM(amount) as total, "
        "COUNT(*) as entries "
        "FROM income "
        "GROUP BY source "
        "ORDER BY total DESC"
    )).fetchall()
    return [
        {
            "source": row[0],
            "total": row[1],
            "entries": row[2]
        }
        for row in result
    ]