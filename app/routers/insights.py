from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.database import get_db
from groq import Groq
from dotenv import load_dotenv
import os

load_dotenv()

router = APIRouter(prefix="/insights", tags=["AI Insights"])

client = Groq(api_key=os.getenv("GROQ_API_KEY"))


@router.get("/summary")
def get_ai_summary(db: Session = Depends(get_db)):
    expenses = db.execute(text("""
        SELECT category, SUM(amount) as total
        FROM expenses
        GROUP BY category
        ORDER BY total DESC
    """)).fetchall()

    total_spent = sum(row[1] for row in expenses)
    breakdown = ", ".join(
        f"{row[0]}: {row[1]}" for row in expenses
    )

    prompt = f"""
    You are SENRA, a personal finance AI assistant.
    
    Here is the user's expense data:
    Total spent: {total_spent}
    Category breakdown: {breakdown}
    
    Give a short, clear, friendly summary in 3-4 sentences:
    1. How much they spent and where
    2. One observation about their spending
    3. One actionable tip to save money
    
    Keep it simple. No jargon.
    """

    response = client.chat.completions.create(
        model="llama-3.1-8b-instant",
        messages=[{"role": "user", "content": prompt}]
    )

    return {
        "total_spent": total_spent,
        "breakdown": [{"category": row[0], "amount": row[1]} for row in expenses],
        "ai_insight": response.choices[0].message.content
    }