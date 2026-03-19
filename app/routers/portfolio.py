from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import Portfolio
from app.schemas import PortfolioCreate, PortfolioOut
from typing import List
import yfinance as yf

router = APIRouter(prefix="/portfolio", tags=["Portfolio"])


@router.post("/", response_model=PortfolioOut)
def add_stock(stock: PortfolioCreate, db: Session = Depends(get_db)):
    new_stock = Portfolio(
        ticker=stock.ticker.upper(),
        buy_price=stock.buy_price,
        quantity=stock.quantity,
        date=stock.date,
        note=stock.note
    )
    db.add(new_stock)
    db.commit()
    db.refresh(new_stock)
    return new_stock


@router.get("/", response_model=List[PortfolioOut])
def get_portfolio(db: Session = Depends(get_db)):
    return db.query(Portfolio).order_by(Portfolio.id.desc()).all()


@router.delete("/{stock_id}")
def delete_stock(stock_id: int, db: Session = Depends(get_db)):
    stock = db.query(Portfolio).filter(Portfolio.id == stock_id).first()
    if not stock:
        raise HTTPException(status_code=404, detail="Stock not found")
    db.delete(stock)
    db.commit()
    return {"message": "Stock deleted successfully"}


@router.get("/live")
def get_live_portfolio(db: Session = Depends(get_db)):
    stocks = db.query(Portfolio).all()
    if not stocks:
        return []

    result = []
    total_invested = 0
    total_current = 0

    for stock in stocks:
        try:
            info = yf.Ticker(stock.ticker).info
            current_price = info.get("currentPrice", stock.buy_price)
        except:
            current_price = stock.buy_price

        invested = stock.buy_price * stock.quantity
        current_value = current_price * stock.quantity
        pnl = current_value - invested
        pnl_pct = (pnl / invested * 100) if invested > 0 else 0

        total_invested += invested
        total_current += current_value

        result.append({
            "id": stock.id,
            "ticker": stock.ticker,
            "quantity": stock.quantity,
            "buy_price": stock.buy_price,
            "current_price": round(current_price, 2),
            "invested": round(invested, 2),
            "current_value": round(current_value, 2),
            "pnl": round(pnl, 2),
            "pnl_pct": round(pnl_pct, 2),
            "date": stock.date,
            "note": stock.note
        })

    return {
        "holdings": result,
        "total_invested": round(total_invested, 2),
        "total_current_value": round(total_current, 2),
        "total_pnl": round(total_current - total_invested, 2),
        "total_pnl_pct": round((total_current - total_invested) / total_invested * 100, 2) if total_invested > 0 else 0
    }