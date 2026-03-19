from fastapi import APIRouter, Query
import yfinance as yf
from datetime import datetime

router = APIRouter(prefix="/stocks", tags=["Stocks"])

# Try nsetools for live Indian data + full symbol list
try:
    from nsetools import Nse
    nse_client = Nse()
    NSE_AVAILABLE = True
except:
    nse_client = None
    NSE_AVAILABLE = False

# Build NSE stock dict safely
ALL_NSE_STOCKS = {}
try:
    if NSE_AVAILABLE:
        raw = nse_client.get_stock_codes()
        if isinstance(raw, dict):
            ALL_NSE_STOCKS = {str(k).upper(): str(v) for k,v in raw.items() if k and str(k).upper() != "SYMBOL"}
        elif isinstance(raw, list):
            # list of dicts like [{"symbol":"RELIANCE","companyName":"Reliance..."}, ...]
            for item in raw:
                if isinstance(item, dict):
                    sym = str(item.get("symbol","")).upper().strip()
                    name = str(item.get("companyName", item.get("name", sym))).strip()
                    if sym and sym != "SYMBOL":
                        ALL_NSE_STOCKS[sym] = name
                elif isinstance(item, str) and item.strip():
                    ALL_NSE_STOCKS[item.upper().strip()] = item.upper().strip()
except:
    ALL_NSE_STOCKS = {}

# Fallback hardcoded list for when nsetools is unavailable
FALLBACK_INDIA = [
    "RELIANCE.NS","TCS.NS","INFY.NS","HDFCBANK.NS","ICICIBANK.NS","WIPRO.NS",
    "SBIN.NS","BAJFINANCE.NS","ADANIENT.NS","ITC.NS","HINDUNILVR.NS","KOTAKBANK.NS",
    "LT.NS","AXISBANK.NS","MARUTI.NS","SUNPHARMA.NS","TITAN.NS","ULTRACEMCO.NS",
    "ASIANPAINT.NS","HCLTECH.NS","ONGC.NS","NTPC.NS","POWERGRID.NS","COALINDIA.NS",
    "TECHM.NS","DIVISLAB.NS","CIPLA.NS","DRREDDY.NS","BPCL.NS","GRASIM.NS",
    "TATAMOTORS.NS","TATASTEEL.NS","JSWSTEEL.NS","HINDALCO.NS","BHARTIARTL.NS",
    "NESTLEIND.NS","BRITANNIA.NS","BAJAJFINSV.NS","HDFCLIFE.NS","SBILIFE.NS",
    "INDUSINDBK.NS","M&M.NS","EICHERMOT.NS","HEROMOTOCO.NS","APOLLOHOSP.NS",
    "TATACONSUM.NS","PIDILITIND.NS","DMART.NS","SHREECEM.NS","ZOMATO.NS",
    "NYKAA.NS","PAYTM.NS","POLICYBZR.NS","IRCTC.NS","HAL.NS","BEL.NS",
    "TATAELXSI.NS","PERSISTENT.NS","COFORGE.NS","LTIM.NS","MPHASIS.NS",
    "BANKBARODA.NS","PNB.NS","CANBK.NS","UNIONBANK.NS","IDFCFIRSTB.NS",
    "FEDERALBNK.NS","RBLBANK.NS","BANDHANBNK.NS","AUBANK.NS","INDIGO.NS",
    "SPICEJET.NS","ADANIPORTS.NS","ADANIGREEN.NS","ADANIPOWER.NS","ADANITRANS.NS",
    "VEDL.NS","NMDC.NS","SAIL.NS","NATIONALUM.NS","HINDZINC.NS",
    "GODREJCP.NS","DABUR.NS","MARICO.NS","COLPAL.NS","EMAMILTD.NS",
    "BALKRISIND.NS","CEAT.NS","APOLLOTYRE.NS","MRF.NS","MOTHERSON.NS",
    "BOSCHLTD.NS","SCHAEFFLER.NS","TIINDIA.NS","SUNDRMFAST.NS","ESCORTS.NS",
    "VOLTAS.NS","BLUESTARCO.NS","HAVELLS.NS","CROMPTON.NS","POLYCAB.NS",
    "DIXON.NS","AMBER.NS","WHIRLPOOL.NS","BATAINDIA.NS","RELAXO.NS",
    "PAGEIND.NS","VSTIND.NS","RADICO.NS","UNITEDSPRT.NS","SRF.NS",
    "PIIND.NS","UPL.NS","COROMANDEL.NS","CHAMBLFERT.NS","GNFC.NS",
    "ASTRAL.NS","SUPREMEIND.NS","ATUL.NS","DEEPAKNI.NS","NAVINFLUOR.NS",
    "LALPATHLAB.NS","METROPOLIS.NS","THYROCARE.NS","VIJAYABANK.NS","IDBI.NS",
]

# Popular NSE ETFs
NSE_ETFS = {
    "ITBEES": "Nippon India ETF Nifty IT",
    "NIFTYBEES": "Nippon India ETF Nifty 50",
    "GOLDBEES": "Nippon India ETF Gold",
    "BANKBEES": "Nippon India ETF Nifty Bank",
    "JUNIORBEES": "Nippon India ETF Junior BeES",
    "LIQUIDBEES": "Nippon India ETF Liquid BeES",
    "SILVERBEES": "Nippon India ETF Silver",
    "PHARMABEES": "Nippon India ETF Nifty Pharma",
    "AUTOIETF": "Nippon India ETF Nifty Auto",
    "INFRABEES": "Nippon India ETF Infra BeES",
    "CPSEETF": "Nippon India ETF CPSE",
    "PSUBNKBEES": "Nippon India ETF Nifty PSU Bank",
    "NETFIT": "Nippon India ETF Nifty IT",
    "SETFNIF50": "SBI Nifty 50 ETF",
    "SETFNN50": "SBI Nifty Next 50 ETF",
    "SETFGOLD": "SBI ETF Gold",
    "ICICINIFTY": "ICICI Prudential Nifty 50 ETF",
    "ICICIB22": "ICICI Prudential Nifty Bank ETF",
    "HNGSNGBEES": "Nippon India ETF Hang Seng BeES",
    "MAFANG": "Mirae Asset NYSE FANG+ ETF",
    "N100": "Nippon India ETF Nifty 100",
    "NIFTYIT": "ICICI Prudential Nifty IT ETF",
    "MON100": "Motilal Oswal Nasdaq 100 ETF",
    "MIDCAPETF": "SBI Nifty Midcap 150 ETF",
    "SMALLCAP": "Nippon India ETF Nifty Smallcap 250",
    "SENSEXETF": "HDFC Sensex ETF",
    "HDFCNIFTY": "HDFC Nifty 50 ETF",
    "AXISNIFTY": "Axis Nifty 50 ETF",
    "KOTAKNIFTY": "Kotak Nifty 50 ETF",
    "SBIETFCON": "SBI ETF Consumption",
}

COUNTRY_TICKERS = {
    "United States": ["AAPL","TSLA","GOOGL","MSFT","AMZN","NVDA","META","NFLX","ORCL","AMD","INTC","IBM","PYPL","UBER","SHOP","SQ","CRWD","PLTR","COIN","ABNB","DASH","RIVN","SOFI","HOOD","RBLX"],
    "United Kingdom": ["LLOY.L","BARC.L","BP.L","SHEL.L","AZN.L","HSBA.L","VOD.L","GSK.L","RIO.L","BT-A.L"],
    "Europe": ["ASML","SAP","MC.PA","OR.PA","SIE.DE","BMW.DE","NESN.SW"],
    "Japan": ["7203.T","6758.T","9984.T","8306.T","6861.T"],
    "Australia": ["CBA.AX","BHP.AX","CSL.AX","ANZ.AX","WBC.AX"],
    "Canada": ["SHOP.TO","RY.TO","TD.TO","CNR.TO","ENB.TO"],
    "Singapore": ["D05.SI","O39.SI","U11.SI","C6L.SI"],
    "UAE": ["EMAAR.AE","DIB.AE","FAB.AE"],
}

DEFAULT_BAND = {
    "India": ["RELIANCE.NS","TCS.NS","INFY.NS","HDFCBANK.NS","ICICIBANK.NS","WIPRO.NS","SBIN.NS","BAJFINANCE.NS","^NSEI","^BSESN"],
    "United States": ["AAPL","TSLA","GOOGL","MSFT","AMZN","NVDA","META","NFLX","^GSPC","^DJI"],
    "United Kingdom": ["LLOY.L","BARC.L","BP.L","SHEL.L","AZN.L"],
    "Europe": ["ASML","SAP","MC.PA","SIE.DE"],
    "Japan": ["7203.T","6758.T","9984.T"],
    "Australia": ["CBA.AX","BHP.AX","CSL.AX"],
    "Canada": ["SHOP.TO","RY.TO","TD.TO"],
    "Singapore": ["D05.SI","O39.SI"],
    "UAE": ["EMAAR.AE","DIB.AE"],
}

INTERVAL_MAP = {
    "1m":  ("7d",  "1m"),
    "5m":  ("60d", "5m"),
    "15m": ("60d", "15m"),
    "1h":  ("60d", "1h"),
    "1d":  ("1y",  "1d"),
    "1wk": ("5y",  "1wk"),
    "1mo": ("max", "1mo"),
}


def nse_live_price(symbol: str):
    if not NSE_AVAILABLE:
        return None
    clean = symbol.upper().replace(".NS","").replace(".BO","")
    try:
        q = nse_client.get_quote(clean)
        if not q:
            return None
        return {
            "price": float(q.get("lastPrice") or q.get("closePrice") or 0),
            "change": float(q.get("change") or 0),
            "change_pct": float(q.get("pChange") or 0),
            "open": float(q.get("open") or 0),
            "high": float(q.get("dayHigh") or 0),
            "low": float(q.get("dayLow") or 0),
            "prev_close": float(q.get("previousClose") or 0),
            "volume": int(q.get("totalTradedVolume") or 0),
            "source": "NSE_LIVE"
        }
    except:
        return None


@router.get("/search")
def search_stocks(q: str = Query(..., min_length=1), country: str = "United States"):
    q_upper = q.strip().upper()
    results = []

    if country == "India":
        # Search full NSE list first
        if ALL_NSE_STOCKS and isinstance(ALL_NSE_STOCKS, dict):
            for symbol, name in ALL_NSE_STOCKS.items():
                sym_up = str(symbol).upper().strip()
                name_up = str(name).upper().strip()
                if sym_up in ("SYMBOL","") or not sym_up:
                    continue
                if sym_up.startswith(q_upper) or q_upper in sym_up or q_upper in name_up:
                    results.append({
                        "ticker": sym_up + ".NS",
                        "name": name if name != symbol else sym_up,
                        "price": 0,
                        "currency": "INR"
                    })
                    if len(results) >= 10:
                        break

        # Search ETFs
        for sym, name in NSE_ETFS.items():
            if sym.startswith(q_upper) or q_upper in sym or q_upper in name.upper():
                if not any(r["ticker"] == sym+".NS" for r in results):
                    results.append({"ticker": sym+".NS", "name": name, "price": 0, "currency": "INR"})
            if len(results) >= 10:
                break

        # If nsetools not available or no results, search fallback list
        if not results:
            for ticker in FALLBACK_INDIA:
                base = ticker.replace(".NS","").replace(".BO","")
                if base.startswith(q_upper) or q_upper in base:
                    results.append({"ticker": ticker, "name": base, "price": 0, "currency": "INR"})
                if len(results) >= 10:
                    break

        # Fetch live prices for top 5 results
        for i, r in enumerate(results[:5]):
            try:
                live = nse_live_price(r["ticker"])
                if live and live["price"] > 0:
                    results[i]["price"] = live["price"]
                else:
                    info = yf.Ticker(r["ticker"]).fast_info
                    results[i]["price"] = round(float(getattr(info, "last_price", 0) or 0), 2)
            except:
                pass

        return results[:10]

    else:
        tickers = COUNTRY_TICKERS.get(country, COUNTRY_TICKERS["United States"])
        for ticker in tickers:
            base = ticker.split(".")[0]
            if base.startswith(q_upper) or q_upper in base:
                try:
                    info = yf.Ticker(ticker).info
                    name = info.get("longName") or info.get("shortName") or base
                    price = info.get("currentPrice") or info.get("regularMarketPrice") or 0
                    results.append({"ticker": ticker, "name": name, "price": round(float(price), 2), "currency": info.get("currency","USD")})
                except:
                    results.append({"ticker": ticker, "name": base, "price": 0, "currency": "USD"})
        return results[:10]


@router.get("/band/prices")
def get_band_prices(country: str = "United States"):
    tickers = DEFAULT_BAND.get(country, DEFAULT_BAND["United States"])
    result = []
    for t in tickers:
        try:
            if country == "India" and not t.startswith("^"):
                live = nse_live_price(t)
                if live and live["price"] > 0:
                    name = t.replace(".NS","").replace(".BO","")
                    result.append({"ticker": name, "price": round(live["price"],2), "change_pct": round(live["change_pct"],2), "currency": "INR"})
                    continue
            info = yf.Ticker(t).info
            price = info.get("currentPrice") or info.get("regularMarketPrice") or 0
            change = info.get("regularMarketChangePercent") or 0
            currency = info.get("currency", "USD")
            name = t.replace("^","").replace(".NS","").replace(".BO","").replace(".L","").replace(".AX","").replace(".TO","")
            result.append({"ticker": name, "price": round(float(price),2), "change_pct": round(float(change),2), "currency": currency})
        except:
            pass
    return result


@router.get("/{ticker}/price")
def get_live_price(ticker: str):
    is_indian = ticker.endswith(".NS") or ticker.endswith(".BO")
    if is_indian:
        live = nse_live_price(ticker)
        if live and live["price"] > 0:
            return {
                "ticker": ticker.upper(),
                "price": round(live["price"], 2),
                "change": round(live["change"], 2),
                "change_pct": round(live["change_pct"], 2),
                "open": round(live["open"], 2),
                "high": round(live["high"], 2),
                "low": round(live["low"], 2),
                "currency": "INR",
                "source": "NSE_LIVE"
            }
    try:
        info = yf.Ticker(ticker).info
        price = info.get("currentPrice") or info.get("regularMarketPrice") or 0
        change = info.get("regularMarketChange") or 0
        change_pct = info.get("regularMarketChangePercent") or 0
        if abs(change_pct) < 1:
            change_pct = change_pct * 100
        return {
            "ticker": ticker.upper(),
            "price": round(float(price), 2),
            "change": round(float(change), 2),
            "change_pct": round(float(change_pct), 2),
            "currency": info.get("currency", "USD"),
            "source": "YFINANCE_DELAYED"
        }
    except Exception as e:
        return {"error": str(e)}


@router.get("/{ticker}/chart")
def get_chart_data(ticker: str, interval: str = "1d"):
    period, ivl = INTERVAL_MAP.get(interval, ("1y", "1d"))
    try:
        stock = yf.Ticker(ticker)
        hist = stock.history(period=period, interval=ivl)
        if hist.empty:
            return {"candles": [], "interval": interval}
        candles = []
        for i in range(len(hist)):
            ts = hist.index[i]
            try:
                t = int(ts.timestamp())
            except:
                t = int(datetime.combine(ts.date(), datetime.min.time()).timestamp())
            o,h,l,c = float(hist["Open"].iloc[i]),float(hist["High"].iloc[i]),float(hist["Low"].iloc[i]),float(hist["Close"].iloc[i])
            if any(x != x for x in [o,h,l,c]):
                continue
            candles.append({"time": t, "open": round(o,4), "high": round(h,4), "low": round(l,4), "close": round(c,4), "volume": int(hist["Volume"].iloc[i])})
        return {"candles": candles, "interval": interval}
    except Exception as e:
        return {"candles": [], "interval": interval, "error": str(e)}


@router.get("/{ticker}/analysis")
def get_stock_analysis(ticker: str):
    stock = yf.Ticker(ticker)
    info = stock.info

    pe = float(info.get("trailingPE") or 0)
    pb = float(info.get("priceToBook") or 0)
    roe = float(info.get("returnOnEquity") or 0)
    revenue_growth = float(info.get("revenueGrowth") or 0)
    profit_margins = float(info.get("profitMargins") or 0)
    debt_to_equity = float(info.get("debtToEquity") or 0)
    current_ratio = float(info.get("currentRatio") or 0)
    week52_high = float(info.get("fiftyTwoWeekHigh") or 0)
    week52_low = float(info.get("fiftyTwoWeekLow") or 0)
    beta = float(info.get("beta") or 1)
    dividend_yield = float(info.get("dividendYield") or 0) * 100
    is_indian = ticker.endswith(".NS") or ticker.endswith(".BO")

    current_price = 0.0
    if is_indian:
        live = nse_live_price(ticker)
        if live and live["price"] > 0:
            current_price = live["price"]
    if not current_price:
        current_price = float(info.get("currentPrice") or info.get("regularMarketPrice") or 0)

    from_high = ((current_price - week52_high) / week52_high * 100) if week52_high else 0
    from_low = ((current_price - week52_low) / week52_low * 100) if week52_low else 0

    def rate(val, low_bad, high_good, reverse=False):
        if reverse:
            if val < low_bad: return "High"
            if val < high_good: return "Avg"
            return "Low"
        if val > high_good: return "High"
        if val > low_bad: return "Avg"
        return "Low"

    scorecard = {
        "performance": rate(roe, 0.05, 0.15),
        "valuation": rate(pe, 15, 30, reverse=True),
        "growth": rate(revenue_growth, 0.05, 0.15),
        "profitability": rate(profit_margins, 0.05, 0.15),
        "entry_point": rate(from_high, -20, -10, reverse=True),
        "red_flags": rate(debt_to_equity, 50, 150, reverse=True),
    }

    signal = "HOLD"
    reason = "Fairly valued — wait for better entry"
    if from_high < -15 and roe > 0.10 and pe < 35:
        signal = "BUY"
        reason = f"Down {abs(from_high):.1f}% from high, ROE {roe*100:.1f}%"
    elif pe > 50 or from_high > -2:
        signal = "SELL"
        reason = "Near 52W high" if from_high > -2 else "PE too high"

    entry_price = round(current_price * 0.97, 2) if signal == "BUY" else round(current_price * 0.93, 2)

    holders = {"promoter": 0.0, "mutual_funds": 0.0, "foreign": 0.0, "retail": 0.0}
    try:
        holders["promoter"] = round(float(info.get("heldPercentInsiders") or 0) * 100, 2)
        holders["foreign"] = round(float(info.get("heldPercentInstitutions") or 0) * 100, 2)
    except: pass
    try:
        mf = stock.mutualfund_holders
        if mf is not None and not mf.empty:
            for col in ["% Out", "pctHeld", "percentHeld"]:
                if col in mf.columns:
                    raw = float(mf[col].sum())
                    holders["mutual_funds"] = round(raw * 100 if raw < 2 else raw, 2)
                    break
    except: pass
    held = holders["promoter"] + holders["foreign"] + holders["mutual_funds"]
    holders["retail"] = round(max(0, 100 - held), 2)

    news = []
    try:
        for n in (stock.news or [])[:6]:
            content = n.get("content", {})
            if isinstance(content, dict):
                title = content.get("title", "")
                pub = str(content.get("pubDate", ""))[:10]
                link_obj = content.get("canonicalUrl", {})
                link = link_obj.get("url", "") if isinstance(link_obj, dict) else ""
                prov = content.get("provider", {})
                source = prov.get("displayName", "") if isinstance(prov, dict) else ""
            else:
                title = n.get("title", "")
                pub = str(n.get("providerPublishTime", ""))[:10]
                link = n.get("link", "")
                source = n.get("publisher", "")
            if title:
                news.append({"title": title, "link": link, "source": source, "published": pub})
    except: pass

    return {
        "scorecard": scorecard,
        "signal": signal,
        "signal_reason": reason,
        "entry_price": entry_price,
        "risk_level": "High" if beta > 1.5 else "Medium" if beta > 0.8 else "Low",
        "metrics": {
            "pe_ratio": round(pe, 2), "pb_ratio": round(pb, 2),
            "roe": round(roe * 100, 2), "revenue_growth": round(revenue_growth * 100, 2),
            "profit_margins": round(profit_margins * 100, 2), "debt_to_equity": round(debt_to_equity, 2),
            "current_ratio": round(current_ratio, 2), "beta": round(beta, 2),
            "dividend_yield": round(dividend_yield, 2),
            "from_52w_high": round(from_high, 2), "from_52w_low": round(from_low, 2),
        },
        "holders": holders,
        "news": news
    }


@router.get("/{ticker}/history")
def get_stock_history(ticker: str, period: str = "6mo"):
    stock = yf.Ticker(ticker)
    hist = stock.history(period=period)
    if hist.empty:
        return {"dates": [], "prices": [], "candles": []}
    dates = [str(d.date()) for d in hist.index]
    prices = [round(float(p), 2) for p in hist["Close"].tolist()]
    candles = [{"time": str(hist.index[i].date()), "open": round(float(hist["Open"].iloc[i]),2), "high": round(float(hist["High"].iloc[i]),2), "low": round(float(hist["Low"].iloc[i]),2), "close": round(float(hist["Close"].iloc[i]),2), "volume": int(hist["Volume"].iloc[i])} for i in range(len(hist))]
    return {"dates": dates, "prices": prices, "candles": candles}


@router.get("/{ticker}")
def get_stock(ticker: str):
    is_indian = ticker.endswith(".NS") or ticker.endswith(".BO")
    info = yf.Ticker(ticker).info
    price = None
    source = "yfinance"

    if is_indian:
        live = nse_live_price(ticker)
        if live and live["price"] > 0:
            price = live["price"]
            source = "nse_live"

    if not price:
        price = info.get("currentPrice") or info.get("regularMarketPrice")

    if not price:
        return {"error": f"Could not find '{ticker}'. For Indian stocks add .NS (e.g. RELIANCE.NS)"}

    return {
        "ticker": ticker.upper(),
        "name": info.get("longName", "N/A"),
        "price": round(float(price), 2),
        "currency": info.get("currency", "INR" if is_indian else "USD"),
        "change_percent": info.get("52WeekChange", "N/A"),
        "market_cap": info.get("marketCap", "N/A"),
        "pe_ratio": info.get("trailingPE", "N/A"),
        "52_week_high": info.get("fiftyTwoWeekHigh", "N/A"),
        "52_week_low": info.get("fiftyTwoWeekLow", "N/A"),
        "volume": info.get("volume", "N/A"),
        "sector": info.get("sector", "N/A"),
        "industry": info.get("industry", "N/A"),
        "source": source
    }