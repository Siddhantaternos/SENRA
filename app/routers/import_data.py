from fastapi import APIRouter, File, UploadFile, Depends
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import Expense, Income
from datetime import datetime
import pandas as pd
import io
import json
import re

router = APIRouter(prefix="/import", tags=["Import"])


def parse_amount(val):
    if val is None:
        return 0.0
    s = str(val).replace(",", "").replace("₹", "").replace("$", "").replace("£", "").strip()
    try:
        return abs(float(s))
    except:
        return 0.0


def parse_date(val):
    if not val:
        return datetime.now().strftime("%Y-%m-%d")
    s = str(val).strip()
    for fmt in ["%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y", "%m/%d/%Y", "%d %b %Y", "%d-%b-%Y", "%d %B %Y", "%Y%m%d"]:
        try:
            return datetime.strptime(s, fmt).strftime("%Y-%m-%d")
        except:
            continue
    return datetime.now().strftime("%Y-%m-%d")


def guess_category(description: str) -> str:
    desc = description.lower()
    cats = {
        "Food": ["swiggy","zomato","food","restaurant","cafe","pizza","burger","hotel","eat","lunch","dinner","breakfast","mcdonalds","kfc","dominos"],
        "Transport": ["uber","ola","rapido","petrol","fuel","diesel","metro","bus","auto","cab","taxi","toll","parking","irctc","train","flight","airline","indigo","spicejet","air india"],
        "Shopping": ["amazon","flipkart","myntra","ajio","meesho","shop","store","mart","mall","retail","cloth","shoe","fashion"],
        "Entertainment": ["netflix","hotstar","prime","spotify","youtube","cinema","movie","ticket","game","pvr","inox","bookmyshow"],
        "Health": ["pharmacy","medicine","doctor","hospital","clinic","apollo","medplus","1mg","health","dental","gym","fitness"],
        "Utilities": ["electricity","water","gas","internet","wifi","broadband","airtel","jio","vodafone","bsnl","bill","recharge","dth"],
        "Education": ["school","college","course","udemy","coursera","tuition","book","study","education"],
        "Investment": ["sip","mutual fund","groww","zerodha","upstox","stock","share","invest","demat"],
        "Transfer": ["neft","imps","upi","transfer","sent","payment","paid","bank"],
        "Salary": ["salary","payroll","ctc","hike","bonus","stipend","income"],
    }
    for cat, keywords in cats.items():
        if any(k in desc for k in keywords):
            return cat
    return "Miscellaneous"


def is_income_row(description: str, amount: float, debit=None, credit=None) -> bool:
    if credit and parse_amount(credit) > 0:
        return True
    if debit and parse_amount(debit) > 0:
        return False
    desc = description.lower()
    income_keywords = ["salary","credit","received","deposit","refund","cashback","dividend","interest","bonus","stipend","income","imps cr","neft cr","upi cr"]
    return any(k in desc for k in income_keywords)


def process_dataframe(df: pd.DataFrame):
    df.columns = [str(c).strip().lower() for c in df.columns]
    expenses = []
    incomes = []

    # Try to detect column types
    date_col = next((c for c in df.columns if any(k in c for k in ["date","dt","time"])), None)
    desc_col = next((c for c in df.columns if any(k in c for k in ["desc","narr","particular","detail","remark","note","transaction","merchant"])), None)
    amount_col = next((c for c in df.columns if any(k in c for k in ["amount","amt","rs","inr","value"]) and "debit" not in c and "credit" not in c), None)
    debit_col = next((c for c in df.columns if "debit" in c or "dr" == c or "withdraw" in c), None)
    credit_col = next((c for c in df.columns if "credit" in c or "cr" == c or "deposit" in c), None)

    if not desc_col:
        desc_col = df.columns[1] if len(df.columns) > 1 else df.columns[0]
    if not date_col:
        date_col = df.columns[0]

    for _, row in df.iterrows():
        try:
            date = parse_date(row.get(date_col, ""))
            desc = str(row.get(desc_col, "")).strip()
            if not desc or desc == "nan":
                continue

            debit_val = row.get(debit_col) if debit_col else None
            credit_val = row.get(credit_col) if credit_col else None

            if debit_col and credit_col:
                d_amt = parse_amount(debit_val)
                c_amt = parse_amount(credit_val)
                if c_amt > 0:
                    cat = guess_category(desc)
                    src = "Salary" if "salary" in desc.lower() else "Other"
                    incomes.append({"date": date, "amount": c_amt, "source": src, "note": desc[:80]})
                elif d_amt > 0:
                    cat = guess_category(desc)
                    expenses.append({"date": date, "amount": d_amt, "category": cat, "note": desc[:80]})
            elif amount_col:
                amt = parse_amount(row.get(amount_col))
                if amt <= 0:
                    continue
                if is_income_row(desc, amt):
                    src = "Salary" if "salary" in desc.lower() else "Other"
                    incomes.append({"date": date, "amount": amt, "source": src, "note": desc[:80]})
                else:
                    cat = guess_category(desc)
                    expenses.append({"date": date, "amount": amt, "category": cat, "note": desc[:80]})
        except:
            continue

    return expenses, incomes


@router.post("/csv")
async def import_csv(file: UploadFile = File(...), db: Session = Depends(get_db)):
    try:
        content = await file.read()
        df = pd.read_csv(io.BytesIO(content), on_bad_lines="skip")
        expenses, incomes = process_dataframe(df)
        return _save_and_respond(expenses, incomes, db)
    except Exception as e:
        return {"error": str(e), "expenses_added": 0, "incomes_added": 0}


@router.post("/excel")
async def import_excel(file: UploadFile = File(...), db: Session = Depends(get_db)):
    try:
        content = await file.read()
        df = pd.read_excel(io.BytesIO(content))
        expenses, incomes = process_dataframe(df)
        return _save_and_respond(expenses, incomes, db)
    except Exception as e:
        return {"error": str(e), "expenses_added": 0, "incomes_added": 0}


@router.post("/preview")
async def preview_import(file: UploadFile = File(...)):
    """Preview parsed data without saving"""
    try:
        content = await file.read()
        fname = file.filename.lower()
        if fname.endswith(".csv"):
            df = pd.read_csv(io.BytesIO(content), on_bad_lines="skip")
        elif fname.endswith((".xlsx", ".xls")):
            df = pd.read_excel(io.BytesIO(content))
        else:
            return {"error": "Unsupported format. Use CSV or Excel (.xlsx/.xls)"}

        expenses, incomes = process_dataframe(df)
        return {
            "total_rows": len(df),
            "expenses_found": len(expenses),
            "incomes_found": len(incomes),
            "expenses_preview": expenses[:5],
            "incomes_preview": incomes[:5],
            "columns_detected": list(df.columns)
        }
    except Exception as e:
        return {"error": str(e)}


@router.post("/confirm")
async def confirm_import(file: UploadFile = File(...), db: Session = Depends(get_db)):
    """Parse and save to DB"""
    try:
        content = await file.read()
        fname = file.filename.lower()
        if fname.endswith(".csv"):
            df = pd.read_csv(io.BytesIO(content), on_bad_lines="skip")
        elif fname.endswith((".xlsx", ".xls")):
            df = pd.read_excel(io.BytesIO(content))
        else:
            return {"error": "Unsupported format. Use CSV or Excel (.xlsx/.xls)"}
        expenses, incomes = process_dataframe(df)
        return _save_and_respond(expenses, incomes, db)
    except Exception as e:
        return {"error": str(e), "expenses_added": 0, "incomes_added": 0}


def _save_and_respond(expenses, incomes, db):
    for e in expenses:
        db.add(Expense(date=e["date"], amount=e["amount"], category=e["category"], note=e["note"]))
    for i in incomes:
        db.add(Income(date=i["date"], amount=i["amount"], source=i["source"], note=i["note"]))
    db.commit()
    return {
        "success": True,
        "expenses_added": len(expenses),
        "incomes_added": len(incomes),
        "total_added": len(expenses) + len(incomes),
        "message": f"Imported {len(expenses)} expenses and {len(incomes)} income entries"
    }