from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import text
from pydantic import BaseModel
from typing import List, Optional
from app.database import get_db
from app.models import Expense, Income, Portfolio
from groq import Groq
from dotenv import load_dotenv
from datetime import datetime
import os
import json
import re

load_dotenv()
router = APIRouter(prefix="/agent", tags=["AI Agent"])
client = Groq(api_key=os.getenv("GROQ_API_KEY"))

class Message(BaseModel):
    role: str
    content: str

class ChatRequest(BaseModel):
    message: str
    history: Optional[List[Message]] = []
    currency: Optional[str] = "$"
    exchange_rate: Optional[float] = 1.0

TOOLS = [
    {"type":"function","function":{"name":"add_expense","description":"Add expense when user mentions spending money.","parameters":{"type":"object","properties":{"amount":{"type":"number","description":"Exact amount as user said, no conversion"},"category":{"type":"string"},"note":{"type":"string"},"date":{"type":"string","description":"YYYY-MM-DD, today if not specified"}},"required":["amount","category","note","date"]}}},
    {"type":"function","function":{"name":"add_income","description":"Add income when user mentions receiving money, salary, freelance.","parameters":{"type":"object","properties":{"amount":{"type":"number","description":"Exact amount as user said, no conversion"},"source":{"type":"string","description":"Salary/Pocket Money/Freelance/Trading Profits/Other"},"note":{"type":"string"},"date":{"type":"string"}},"required":["amount","source","note","date"]}}},
    {"type":"function","function":{"name":"add_stock","description":"Add stock to portfolio when user mentions buying shares.","parameters":{"type":"object","properties":{"ticker":{"type":"string"},"buy_price":{"type":"number","description":"Exact price as user said, no conversion"},"quantity":{"type":"number"},"note":{"type":"string"},"date":{"type":"string"}},"required":["ticker","buy_price","quantity","date"]}}},
    {"type":"function","function":{"name":"get_summary","description":"Get financial summary when user asks about finances, savings, spending.","parameters":{"type":"object","properties":{},"required":[]}}},
    {"type":"function","function":{"name":"get_expense_breakdown","description":"Get expense breakdown when user asks about top expenses or spending categories.","parameters":{"type":"object","properties":{},"required":[]}}}
]

TOOL_NAMES = {"add_expense","add_income","add_stock","get_summary","get_expense_breakdown"}

def clean_reply(text: str) -> str:
    if not text:
        return ""
    text = re.sub(r'<function=\w+>.*?</function>', '', text, flags=re.DOTALL)
    text = re.sub(r'<function=\w+>.*', '', text, flags=re.DOTALL)
    text = re.sub(r'function=\w+>\{.*?\}', '', text, flags=re.DOTALL)
    text = re.sub(r'\{"amount".*?\}', '', text, flags=re.DOTALL)
    text = re.sub(r'\{"ticker".*?\}', '', text, flags=re.DOTALL)
    text = re.sub(r'\{"source".*?\}', '', text, flags=re.DOTALL)
    text = text.strip()
    return text if text else "Done."

def execute_tool(name, args, db):
    today = datetime.now().strftime("%Y-%m-%d")
    if name == "add_expense":
        db.add(Expense(date=args.get("date",today), amount=args["amount"], category=args["category"], note=args["note"]))
        db.commit()
        total = db.execute(text("SELECT IFNULL(SUM(amount),0) FROM expenses WHERE strftime('%Y-%m',date)=strftime('%Y-%m','now')")).scalar()
        return json.dumps({"saved":True,"amount":args["amount"],"category":args["category"],"month_total":round(total,2)})
    elif name == "add_income":
        db.add(Income(date=args.get("date",today), amount=args["amount"], source=args["source"], note=args["note"]))
        db.commit()
        total = db.execute(text("SELECT IFNULL(SUM(amount),0) FROM income WHERE strftime('%Y-%m',date)=strftime('%Y-%m','now')")).scalar()
        return json.dumps({"saved":True,"amount":args["amount"],"source":args["source"],"month_total":round(total,2)})
    elif name == "add_stock":
        db.add(Portfolio(ticker=args["ticker"].upper(), buy_price=args["buy_price"], quantity=args["quantity"], date=args.get("date",today), note=args.get("note","")))
        db.commit()
        total = db.execute(text("SELECT IFNULL(SUM(buy_price*quantity),0) FROM portfolio")).scalar()
        return json.dumps({"saved":True,"ticker":args["ticker"].upper(),"qty":args["quantity"],"price":args["buy_price"],"total_invested":round(total,2)})
    elif name == "get_summary":
        inc = db.execute(text("SELECT IFNULL(SUM(amount),0) FROM income")).scalar()
        exp = db.execute(text("SELECT IFNULL(SUM(amount),0) FROM expenses")).scalar()
        inv = db.execute(text("SELECT IFNULL(SUM(buy_price*quantity),0) FROM portfolio")).scalar()
        m_inc = db.execute(text("SELECT IFNULL(SUM(amount),0) FROM income WHERE strftime('%Y-%m',date)=strftime('%Y-%m','now')")).scalar()
        m_exp = db.execute(text("SELECT IFNULL(SUM(amount),0) FROM expenses WHERE strftime('%Y-%m',date)=strftime('%Y-%m','now')")).scalar()
        cats = db.execute(text("SELECT category,SUM(amount) as t FROM expenses GROUP BY category ORDER BY t DESC LIMIT 3")).fetchall()
        return json.dumps({"income":round(inc,2),"expenses":round(exp,2),"invested":round(inv,2),"savings":round(inc-exp-inv,2),"month_income":round(m_inc,2),"month_expenses":round(m_exp,2),"month_saved":round(m_inc-m_exp,2),"top_cats":[{"cat":r[0],"total":round(r[1],2)} for r in cats]})
    elif name == "get_expense_breakdown":
        total = db.execute(text("SELECT IFNULL(SUM(amount),0) FROM expenses")).scalar()
        cats = db.execute(text("SELECT category,SUM(amount) as t,COUNT(*) as c FROM expenses GROUP BY category ORDER BY t DESC")).fetchall()
        return json.dumps({"total":round(total,2),"breakdown":[{"cat":r[0],"total":round(r[1],2),"count":r[2],"pct":round(r[1]/total*100,1) if total>0 else 0} for r in cats]})
    return json.dumps({"error":"unknown tool"})

@router.post("/chat")
def agent_chat(request: ChatRequest, db: Session = Depends(get_db)):
    today = datetime.now().strftime("%Y-%m-%d")
    cur = request.currency

    system_prompt = f"""You are SENRA, a finance AI. Today: {today}. User currency: {cur}.

CRITICAL RULES:
- NEVER convert or multiply amounts. Save EXACTLY what the user says.
- If user says "spent 500", save 500. If user says "salary 50000", save 50000.
- Max 3 lines per reply. No exceptions.
- Never output raw JSON, function calls, or code.
- No greetings, no filler words.
- Only use tools: add_expense, add_income, add_stock, get_summary, get_expense_breakdown.
- For stock questions: answer in plain text, no tools.

REPLY FORMATS:
Expense: ✓ [Category] {cur}[amount] saved | Month total: {cur}[total]
Income: ✓ [Source] {cur}[amount] saved | Month total: {cur}[total]
Stock: ✓ [QTY]x[TICKER] @ {cur}[price]
Summary: Earned {cur}X · Spent {cur}X · Saved {cur}X · Invested {cur}X
Month: +{cur}X earned · -{cur}X spent · ={cur}X saved
Stock tip: BUY/SELL/HOLD — [reason] · Entry: {cur}X · Risk: Low/Med/High"""

    messages = [{"role":"system","content":system_prompt}]
    for msg in request.history[-4:]:
        messages.append({"role":msg.role,"content":msg.content})
    messages.append({"role":"user","content":request.message})

    try:
        response = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=messages,
            tools=TOOLS,
            tool_choice="auto",
            max_tokens=250
        )
    except Exception as e:
        return {"reply": f"Agent error: {str(e)}", "actions": [], "refresh": False}

    response_message = response.choices[0].message
    tool_calls = response_message.tool_calls
    actions_taken = []

    if tool_calls:
        valid = [tc for tc in tool_calls if tc.function.name in TOOL_NAMES]
        if not valid:
            reply = clean_reply(response_message.content or "")
            return {"reply": reply or "How can I help?", "actions": [], "refresh": False}

        messages.append(response_message)
        for tc in valid:
            fn_name = tc.function.name
            try:
                fn_args = json.loads(tc.function.arguments)
            except:
                fn_args = {}
            result = execute_tool(fn_name, fn_args, db)
            actions_taken.append({"tool": fn_name, "args": fn_args})
            messages.append({"tool_call_id": tc.id, "role": "tool", "name": fn_name, "content": result})

        try:
            final = client.chat.completions.create(
                model="llama-3.1-8b-instant",
                messages=messages,
                max_tokens=150
            )
            reply = clean_reply(final.choices[0].message.content or "")
        except:
            reply = "✓ Done"
    else:
        reply = clean_reply(response_message.content or "")

    return {"reply": reply or "Done.", "actions": actions_taken, "refresh": len(actions_taken) > 0}