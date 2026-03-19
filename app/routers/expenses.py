from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.database import get_db
from app.models import Expense
from app.schemas import ExpenseCreate, ExpenseOut
from typing import List

router = APIRouter(prefix="/expenses", tags=["Expenses"])


@router.post("/", response_model=ExpenseOut)
def add_expense(expense: ExpenseCreate, db: Session = Depends(get_db)):
    new_expense = Expense(
        date=expense.date,
        amount=expense.amount,
        category=expense.category,
        note=expense.note
    )
    db.add(new_expense)
    db.commit()
    db.refresh(new_expense)
    return new_expense


@router.get("/", response_model=List[ExpenseOut])
def get_expenses(db: Session = Depends(get_db)):
    return db.query(Expense).order_by(Expense.id.desc()).all()


@router.get("/summary/monthly")
def monthly_summary(db: Session = Depends(get_db)):
    result = db.execute(text(
        "SELECT strftime('%Y-%m', date) as month, "
        "SUM(amount) as total_spent, "
        "COUNT(*) as total_transactions "
        "FROM expenses "
        "GROUP BY month "
        "ORDER BY month DESC"
    )).fetchall()
    return [
        {
            "month": row[0],
            "total_spent": row[1],
            "total_transactions": row[2]
        }
        for row in result
    ]


@router.get("/summary/categories")
def category_summary(db: Session = Depends(get_db)):
    result = db.execute(text(
        "SELECT category, "
        "SUM(amount) as total_spent, "
        "COUNT(*) as total_transactions "
        "FROM expenses "
        "GROUP BY category "
        "ORDER BY total_spent DESC"
    )).fetchall()
    return [
        {
            "category": row[0],
            "total_spent": row[1],
            "total_transactions": row[2]
        }
        for row in result
    ]


@router.delete("/{expense_id}")
def delete_expense(expense_id: int, db: Session = Depends(get_db)):
    expense = db.query(Expense).filter(Expense.id == expense_id).first()
    if not expense:
        raise HTTPException(status_code=404, detail="Expense not found")
    db.delete(expense)
    db.commit()
    return {"message": "Expense deleted successfully"}