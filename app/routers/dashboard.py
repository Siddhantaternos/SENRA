from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.database import get_db

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


@router.get("/overview")
def get_overview(db: Session = Depends(get_db)):
    # Total income all time
    total_income = db.execute(text(
        "SELECT IFNULL(SUM(amount), 0) FROM income"
    )).scalar()

    # Total expenses all time
    total_expenses = db.execute(text(
        "SELECT IFNULL(SUM(amount), 0) FROM expenses"
    )).scalar()

    # Total invested all time
    total_invested = db.execute(text(
        "SELECT IFNULL(SUM(buy_price * quantity), 0) FROM portfolio"
    )).scalar()

    # Savings = income - expenses - invested
    savings = total_income - total_expenses - total_invested

    # This month
    this_month_income = db.execute(text(
        "SELECT IFNULL(SUM(amount), 0) FROM income "
        "WHERE strftime('%Y-%m', date) = strftime('%Y-%m', 'now')"
    )).scalar()

    this_month_expenses = db.execute(text(
        "SELECT IFNULL(SUM(amount), 0) FROM expenses "
        "WHERE strftime('%Y-%m', date) = strftime('%Y-%m', 'now')"
    )).scalar()

    # Monthly breakdown
    monthly = db.execute(text("""
        SELECT
            m,
            IFNULL(i, 0) as income,
            IFNULL(e, 0) as expenses,
            IFNULL(i, 0) - IFNULL(e, 0) as saved
        FROM (
            SELECT strftime('%Y-%m', date) as m, SUM(amount) as i
            FROM income GROUP BY m
        ) inc
        LEFT JOIN (
            SELECT strftime('%Y-%m', date) as m, SUM(amount) as e
            FROM expenses GROUP BY m
        ) exp USING(m)
        ORDER BY m DESC
        LIMIT 12
    """)).fetchall()

    # Income by source
    by_source = db.execute(text(
        "SELECT source, SUM(amount) as total "
        "FROM income GROUP BY source ORDER BY total DESC"
    )).fetchall()

    # Expenses by category
    by_category = db.execute(text(
        "SELECT category, SUM(amount) as total "
        "FROM expenses GROUP BY category ORDER BY total DESC"
    )).fetchall()

    return {
        "all_time": {
            "total_income": round(total_income, 2),
            "total_expenses": round(total_expenses, 2),
            "total_invested": round(total_invested, 2),
            "savings": round(savings, 2)
        },
        "this_month": {
            "income": round(this_month_income, 2),
            "expenses": round(this_month_expenses, 2),
            "saved": round(this_month_income - this_month_expenses, 2)
        },
        "monthly_breakdown": [
            {
                "month": row[0],
                "income": round(row[1], 2),
                "expenses": round(row[2], 2),
                "saved": round(row[3], 2)
            }
            for row in monthly
        ],
        "income_by_source": [
            {"source": row[0], "total": round(row[1], 2)}
            for row in by_source
        ],
        "expenses_by_category": [
            {"category": row[0], "total": round(row[1], 2)}
            for row in by_category
        ]
    }