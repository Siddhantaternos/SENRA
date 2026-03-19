from fastapi import APIRouter
import yfinance as yf

router = APIRouter(prefix="/nse", tags=["NSE Live"])

# Try nsetools first, fallback to yfinance
try:
    from nsetools import Nse
    nse_client = Nse()
    NSE_AVAILABLE = True
except:
    NSE_AVAILABLE = False


def get_live_quote_nse(symbol: str):
    """Get real-time quote from NSE via nsetools"""
    clean = symbol.upper().replace(".NS", "").replace(".BO", "")
    try:
        q = nse_client.get_quote(clean)
        if not q:
            return None
        price = q.get("lastPrice") or q.get("closePrice") or 0
        change = q.get("change") or 0
        change_pct = q.get("pChange") or 0
        open_ = q.get("open") or 0
        high = q.get("dayHigh") or 0
        low = q.get("dayLow") or 0
        prev_close = q.get("previousClose") or 0
        volume = q.get("totalTradedVolume") or 0
        return {
            "ticker": clean,
            "price": round(float(price), 2),
            "change": round(float(change), 2),
            "change_pct": round(float(change_pct), 2),
            "open": round(float(open_), 2),
            "high": round(float(high), 2),
            "low": round(float(low), 2),
            "prev_close": round(float(prev_close), 2),
            "volume": int(volume),
            "currency": "INR",
            "source": "NSE_LIVE"
        }
    except:
        return None


def get_live_quote_yf(symbol: str):
    """Fallback to yFinance"""
    try:
        info = yf.Ticker(symbol).info
        price = info.get("currentPrice") or info.get("regularMarketPrice") or 0
        change = info.get("regularMarketChange") or 0
        change_pct = info.get("regularMarketChangePercent") or 0
        return {
            "ticker": symbol.upper(),
            "price": round(float(price), 2),
            "change": round(float(change), 2),
            "change_pct": round(float(change_pct) * 100, 2) if abs(change_pct) < 1 else round(float(change_pct), 2),
            "open": round(float(info.get("regularMarketOpen") or 0), 2),
            "high": round(float(info.get("dayHigh") or 0), 2),
            "low": round(float(info.get("dayLow") or 0), 2),
            "prev_close": round(float(info.get("previousClose") or 0), 2),
            "volume": int(info.get("volume") or 0),
            "currency": info.get("currency", "INR"),
            "source": "YFINANCE_DELAYED"
        }
    except:
        return None


@router.get("/quote/{symbol}")
def get_quote(symbol: str):
    is_indian = symbol.endswith(".NS") or symbol.endswith(".BO") or "." not in symbol
    if is_indian and NSE_AVAILABLE:
        result = get_live_quote_nse(symbol)
        if result:
            return result
    result = get_live_quote_yf(symbol if "." in symbol else symbol + ".NS")
    if result:
        return result
    return {"error": f"Could not fetch quote for {symbol}"}


@router.get("/market/status")
def market_status():
    try:
        if NSE_AVAILABLE:
            is_open = nse_client.is_valid_code("RELIANCE")
            return {"market": "NSE", "status": "open" if is_open else "closed", "source": "nsetools"}
    except:
        pass
    from datetime import datetime
    import pytz
    ist = pytz.timezone("Asia/Kolkata")
    now = datetime.now(ist)
    weekday = now.weekday()
    hour = now.hour
    minute = now.minute
    time_val = hour * 60 + minute
    is_open = weekday < 5 and 555 <= time_val <= 930
    return {"market": "NSE", "status": "open" if is_open else "closed", "time_ist": now.strftime("%H:%M"), "source": "calculated"}


@router.get("/gainers")
def top_gainers():
    try:
        if NSE_AVAILABLE:
            gainers = nse_client.get_top_gainers()
            return [{"symbol": g.get("symbol",""), "ltp": g.get("ltp",0), "change": g.get("netPrice",0), "change_pct": g.get("percentChange",0)} for g in (gainers or [])[:10]]
    except:
        pass
    return []


@router.get("/losers")
def top_losers():
    try:
        if NSE_AVAILABLE:
            losers = nse_client.get_top_losers()
            return [{"symbol": l.get("symbol",""), "ltp": l.get("ltp",0), "change": l.get("netPrice",0), "change_pct": l.get("percentChange",0)} for l in (losers or [])[:10]]
    except:
        pass
    return []