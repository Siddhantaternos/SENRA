from sqlalchemy import Column, Integer, Float, String, Boolean
from app.database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    full_name = Column(String)
    email = Column(String, unique=True, index=True)
    whatsapp = Column(String)
    country = Column(String)
    currency = Column(String, default="USD")
    currency_symbol = Column(String, default="$")
    hashed_password = Column(String)
    created_at = Column(String)


class Expense(Base):
    __tablename__ = "expenses"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, default=1)
    date = Column(String)
    amount = Column(Float)
    category = Column(String)
    note = Column(String)


class Income(Base):
    __tablename__ = "income"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, default=1)
    date = Column(String)
    amount = Column(Float)
    source = Column(String)
    note = Column(String)


class Portfolio(Base):
    __tablename__ = "portfolio"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, default=1)
    ticker = Column(String)
    buy_price = Column(Float)
    quantity = Column(Float)
    date = Column(String)
    note = Column(String)