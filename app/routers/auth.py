from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import datetime, timedelta
from app.database import get_db
from app.models import User
from passlib.context import CryptContext
from jose import JWTError, jwt
import os

router = APIRouter(prefix="/auth", tags=["Auth"])

SECRET_KEY = os.getenv("SECRET_KEY", "senra-secret-key-change-in-production")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_DAYS = 30

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

COUNTRY_CURRENCY_MAP = {
    "India": {"code": "INR", "symbol": "₹"},
    "United States": {"code": "USD", "symbol": "$"},
    "United Kingdom": {"code": "GBP", "symbol": "£"},
    "Europe": {"code": "EUR", "symbol": "€"},
    "Japan": {"code": "JPY", "symbol": "¥"},
    "Australia": {"code": "AUD", "symbol": "A$"},
    "Canada": {"code": "CAD", "symbol": "C$"},
    "Singapore": {"code": "SGD", "symbol": "S$"},
    "UAE": {"code": "AED", "symbol": "AED"},
}

COUNTRY_STOCKS = {
    "India": ["RELIANCE.NS", "TCS.NS", "INFY.NS", "HDFCBANK.NS", "ICICIBANK.NS", "WIPRO.NS", "SBIN.NS", "BAJFINANCE.NS", "ADANIENT.NS", "ITC.NS"],
    "United States": ["AAPL", "TSLA", "GOOGL", "MSFT", "AMZN", "NVDA", "META", "NFLX", "^GSPC", "^DJI"],
    "United Kingdom": ["LLOY.L", "BARC.L", "BP.L", "SHEL.L", "AZN.L"],
    "Europe": ["ASML", "SAP", "NESN.SW", "LVMH.PA"],
    "Japan": ["7203.T", "6758.T", "9984.T", "8306.T"],
    "Australia": ["CBA.AX", "BHP.AX", "CSL.AX", "ANZ.AX"],
    "Canada": ["SHOP.TO", "RY.TO", "TD.TO", "CNR.TO"],
    "Singapore": ["D05.SI", "O39.SI", "U11.SI"],
    "UAE": ["EMAAR.AE", "DIB.AE", "FAB.AE"],
}


class RegisterRequest(BaseModel):
    full_name: str
    email: str
    whatsapp: str
    country: str
    password: str


class LoginRequest(BaseModel):
    email: str
    password: str


class UpdateProfileRequest(BaseModel):
    full_name: Optional[str] = None
    whatsapp: Optional[str] = None
    country: Optional[str] = None
    new_password: Optional[str] = None


def hash_password(password: str):
    return pwd_context.hash(password)


def verify_password(plain: str, hashed: str):
    return pwd_context.verify(plain, hashed)


def create_token(data: dict):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(days=ACCESS_TOKEN_EXPIRE_DAYS)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def get_current_user(token: str, db: Session):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = payload.get("sub")
        if not user_id:
            return None
        return db.query(User).filter(User.id == int(user_id)).first()
    except JWTError:
        return None


@router.post("/register")
def register(req: RegisterRequest, db: Session = Depends(get_db)):
    existing = db.query(User).filter(User.email == req.email).first()
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")

    currency_info = COUNTRY_CURRENCY_MAP.get(req.country, {"code": "USD", "symbol": "$"})

    user = User(
        full_name=req.full_name,
        email=req.email,
        whatsapp=req.whatsapp,
        country=req.country,
        currency=currency_info["code"],
        currency_symbol=currency_info["symbol"],
        hashed_password=hash_password(req.password),
        created_at=datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    token = create_token({"sub": str(user.id)})

    return {
        "token": token,
        "user": {
            "id": user.id,
            "full_name": user.full_name,
            "email": user.email,
            "country": user.country,
            "currency": user.currency,
            "currency_symbol": user.currency_symbol,
            "whatsapp": user.whatsapp
        },
        "band_tickers": COUNTRY_STOCKS.get(req.country, COUNTRY_STOCKS["United States"])
    }


@router.post("/login")
def login(req: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == req.email).first()
    if not user or not verify_password(req.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid email or password")

    token = create_token({"sub": str(user.id)})

    return {
        "token": token,
        "user": {
            "id": user.id,
            "full_name": user.full_name,
            "email": user.email,
            "country": user.country,
            "currency": user.currency,
            "currency_symbol": user.currency_symbol,
            "whatsapp": user.whatsapp
        },
        "band_tickers": COUNTRY_STOCKS.get(user.country, COUNTRY_STOCKS["United States"])
    }


@router.get("/me")
def get_me(token: str, db: Session = Depends(get_db)):
    user = get_current_user(token, db)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid token")
    return {
        "id": user.id,
        "full_name": user.full_name,
        "email": user.email,
        "country": user.country,
        "currency": user.currency,
        "currency_symbol": user.currency_symbol,
        "whatsapp": user.whatsapp,
        "band_tickers": COUNTRY_STOCKS.get(user.country, COUNTRY_STOCKS["United States"])
    }


@router.put("/profile")
def update_profile(token: str, req: UpdateProfileRequest, db: Session = Depends(get_db)):
    user = get_current_user(token, db)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid token")

    if req.full_name:
        user.full_name = req.full_name
    if req.whatsapp:
        user.whatsapp = req.whatsapp
    if req.country:
        currency_info = COUNTRY_CURRENCY_MAP.get(req.country, {"code": "USD", "symbol": "$"})
        user.country = req.country
        user.currency = currency_info["code"]
        user.currency_symbol = currency_info["symbol"]
    if req.new_password:
        user.hashed_password = hash_password(req.new_password)

    db.commit()
    db.refresh(user)

    return {
        "user": {
            "id": user.id,
            "full_name": user.full_name,
            "email": user.email,
            "country": user.country,
            "currency": user.currency,
            "currency_symbol": user.currency_symbol,
            "whatsapp": user.whatsapp
        },
        "band_tickers": COUNTRY_STOCKS.get(user.country, COUNTRY_STOCKS["United States"])
    }


@router.get("/countries")
def get_countries():
    return [
        {"name": k, "currency_code": v["code"], "currency_symbol": v["symbol"]}
        for k, v in COUNTRY_CURRENCY_MAP.items()
    ]