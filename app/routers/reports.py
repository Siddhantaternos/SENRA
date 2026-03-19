from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.database import get_db
from app.models import User
from app.routers.auth import get_current_user
from datetime import datetime
import io

router = APIRouter(prefix="/reports", tags=["Reports"])


def generate_monthly_pdf(user, month_data: dict, month_str: str) -> bytes:
    from reportlab.lib.pagesizes import A4
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.lib import colors
    from reportlab.lib.units import mm

    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, topMargin=15*mm, bottomMargin=15*mm, leftMargin=20*mm, rightMargin=20*mm)

    BG = colors.HexColor("#060C1A")
    BG2 = colors.HexColor("#0A1628")
    BG3 = colors.HexColor("#0D1F3C")
    CYAN = colors.HexColor("#38BDF8")
    GREEN = colors.HexColor("#22C55E")
    RED = colors.HexColor("#EF4444")
    PURPLE = colors.HexColor("#A78BFA")
    MUTED = colors.HexColor("#64748B")
    TEXT = colors.HexColor("#E2E8F0")
    WHITE = colors.white

    def style(name, **kwargs):
        return ParagraphStyle(name, **kwargs)

    title_style = style("title", fontSize=24, textColor=CYAN, fontName="Helvetica-Bold", spaceAfter=2)
    sub_style = style("sub", fontSize=11, textColor=MUTED, fontName="Helvetica", spaceAfter=12)
    h2_style = style("h2", fontSize=13, textColor=TEXT, fontName="Helvetica-Bold", spaceBefore=14, spaceAfter=6)
    label_style = style("label", fontSize=9, textColor=MUTED, fontName="Helvetica")
    normal_style = style("normal", fontSize=10, textColor=TEXT, fontName="Helvetica")

    cur = user.currency_symbol or "₹"
    story = []

    # Header
    story.append(Paragraph("SENRA", title_style))
    story.append(Paragraph(f"Monthly Financial Report — {month_str}", sub_style))
    story.append(Paragraph(f"Prepared for: {user.full_name}  |  {user.email}  |  {user.country}", label_style))
    story.append(Spacer(1, 6*mm))
    story.append(HRFlowable(width="100%", thickness=1, color=BG3))
    story.append(Spacer(1, 4*mm))

    # Summary cards
    story.append(Paragraph("Summary", h2_style))
    earned = month_data.get("income", 0)
    spent = month_data.get("expenses", 0)
    saved = earned - spent
    invested = month_data.get("invested", 0)

    summary_data = [
        ["", "Earned", "Spent", "Saved", "Invested"],
        ["", f"{cur}{earned:,.2f}", f"{cur}{spent:,.2f}", f"{cur}{saved:,.2f}", f"{cur}{invested:,.2f}"],
    ]
    summary_table = Table(summary_data, colWidths=[10*mm, 42*mm, 42*mm, 42*mm, 42*mm])
    summary_table.setStyle(TableStyle([
        ("BACKGROUND", (1,0), (1,1), colors.HexColor("#14532d")),
        ("BACKGROUND", (2,0), (2,1), colors.HexColor("#450a0a")),
        ("BACKGROUND", (3,0), (3,1), colors.HexColor("#042c53")),
        ("BACKGROUND", (4,0), (4,1), colors.HexColor("#2e1065")),
        ("TEXTCOLOR", (1,0), (1,1), GREEN),
        ("TEXTCOLOR", (2,0), (2,1), RED),
        ("TEXTCOLOR", (3,0), (3,1), CYAN),
        ("TEXTCOLOR", (4,0), (4,1), PURPLE),
        ("ALIGN", (0,0), (-1,-1), "CENTER"),
        ("FONTNAME", (0,0), (-1,0), "Helvetica"),
        ("FONTNAME", (0,1), (-1,1), "Helvetica-Bold"),
        ("FONTSIZE", (0,0), (-1,0), 9),
        ("FONTSIZE", (0,1), (-1,1), 13),
        ("ROWBACKGROUNDS", (0,0), (-1,-1), [None]),
        ("ROUNDEDCORNERS", [4, 4, 4, 4]),
        ("TOPPADDING", (0,0), (-1,-1), 8),
        ("BOTTOMPADDING", (0,0), (-1,-1), 8),
        ("LEFTPADDING", (0,0), (-1,-1), 6),
        ("RIGHTPADDING", (0,0), (-1,-1), 6),
        ("GRID", (1,0), (-1,-1), 0.5, BG3),
    ]))
    story.append(summary_table)
    story.append(Spacer(1, 6*mm))

    # Expenses by category
    if month_data.get("expense_breakdown"):
        story.append(HRFlowable(width="100%", thickness=0.5, color=BG3))
        story.append(Paragraph("Expenses by Category", h2_style))
        cat_data = [["Category", "Amount", "Transactions", "% of Total"]]
        total_exp = sum(r["total"] for r in month_data["expense_breakdown"]) or 1
        for r in month_data["expense_breakdown"]:
            pct = r["total"] / total_exp * 100
            cat_data.append([r["category"], f"{cur}{r['total']:,.2f}", str(r["count"]), f"{pct:.1f}%"])
        cat_table = Table(cat_data, colWidths=[70*mm, 45*mm, 35*mm, 28*mm])
        cat_table.setStyle(TableStyle([
            ("BACKGROUND", (0,0), (-1,0), BG3),
            ("TEXTCOLOR", (0,0), (-1,0), MUTED),
            ("TEXTCOLOR", (0,1), (-1,-1), TEXT),
            ("TEXTCOLOR", (1,1), (1,-1), RED),
            ("FONTNAME", (0,0), (-1,0), "Helvetica"),
            ("FONTNAME", (0,1), (-1,-1), "Helvetica"),
            ("FONTSIZE", (0,0), (-1,-1), 9),
            ("ALIGN", (1,0), (-1,-1), "RIGHT"),
            ("ROWBACKGROUNDS", (0,1), (-1,-1), [colors.HexColor("#0A1628"), colors.HexColor("#060C1A")]),
            ("GRID", (0,0), (-1,-1), 0.3, BG3),
            ("TOPPADDING", (0,0), (-1,-1), 6),
            ("BOTTOMPADDING", (0,0), (-1,-1), 6),
        ]))
        story.append(cat_table)
        story.append(Spacer(1, 6*mm))

    # Income by source
    if month_data.get("income_breakdown"):
        story.append(HRFlowable(width="100%", thickness=0.5, color=BG3))
        story.append(Paragraph("Income by Source", h2_style))
        inc_data = [["Source", "Amount", "Transactions"]]
        for r in month_data["income_breakdown"]:
            inc_data.append([r["source"], f"{cur}{r['total']:,.2f}", str(r["count"])])
        inc_table = Table(inc_data, colWidths=[90*mm, 55*mm, 35*mm])
        inc_table.setStyle(TableStyle([
            ("BACKGROUND", (0,0), (-1,0), BG3),
            ("TEXTCOLOR", (0,0), (-1,0), MUTED),
            ("TEXTCOLOR", (0,1), (-1,-1), TEXT),
            ("TEXTCOLOR", (1,1), (1,-1), GREEN),
            ("FONTNAME", (0,0), (-1,-1), "Helvetica"),
            ("FONTSIZE", (0,0), (-1,-1), 9),
            ("ALIGN", (1,0), (-1,-1), "RIGHT"),
            ("ROWBACKGROUNDS", (0,1), (-1,-1), [colors.HexColor("#0A1628"), colors.HexColor("#060C1A")]),
            ("GRID", (0,0), (-1,-1), 0.3, BG3),
            ("TOPPADDING", (0,0), (-1,-1), 6),
            ("BOTTOMPADDING", (0,0), (-1,-1), 6),
        ]))
        story.append(inc_table)
        story.append(Spacer(1, 6*mm))

    # Recent transactions
    if month_data.get("recent_expenses"):
        story.append(HRFlowable(width="100%", thickness=0.5, color=BG3))
        story.append(Paragraph("Recent Expenses (last 10)", h2_style))
        txn_data = [["Date", "Category", "Note", "Amount"]]
        for r in month_data["recent_expenses"][:10]:
            txn_data.append([r["date"], r["category"], r["note"][:35], f"{cur}{r['amount']:,.2f}"])
        txn_table = Table(txn_data, colWidths=[28*mm, 35*mm, 85*mm, 30*mm])
        txn_table.setStyle(TableStyle([
            ("BACKGROUND", (0,0), (-1,0), BG3),
            ("TEXTCOLOR", (0,0), (-1,0), MUTED),
            ("TEXTCOLOR", (0,1), (-1,-1), TEXT),
            ("TEXTCOLOR", (3,1), (3,-1), RED),
            ("FONTNAME", (0,0), (-1,-1), "Helvetica"),
            ("FONTSIZE", (0,0), (-1,-1), 8),
            ("ALIGN", (3,0), (3,-1), "RIGHT"),
            ("ROWBACKGROUNDS", (0,1), (-1,-1), [colors.HexColor("#0A1628"), colors.HexColor("#060C1A")]),
            ("GRID", (0,0), (-1,-1), 0.3, BG3),
            ("TOPPADDING", (0,0), (-1,-1), 5),
            ("BOTTOMPADDING", (0,0), (-1,-1), 5),
        ]))
        story.append(txn_table)

    # Footer
    story.append(Spacer(1, 8*mm))
    story.append(HRFlowable(width="100%", thickness=0.5, color=BG3))
    story.append(Spacer(1, 3*mm))
    story.append(Paragraph(f"Generated by SENRA · {datetime.now().strftime('%d %b %Y %H:%M')} · senra.app", label_style))

    doc.build(story)
    return buf.getvalue()


@router.get("/monthly")
def download_monthly_report(token: str, month: str = None, db: Session = Depends(get_db)):
    user = get_current_user(token, db)
    if not user:
        from fastapi import HTTPException
        raise HTTPException(status_code=401, detail="Invalid token")

    if not month:
        month = datetime.now().strftime("%Y-%m")

    month_data = {}
    try:
        month_data["income"] = db.execute(text(
            f"SELECT IFNULL(SUM(amount),0) FROM income WHERE strftime('%Y-%m',date)=:m"), {"m": month}).scalar()
        month_data["expenses"] = db.execute(text(
            f"SELECT IFNULL(SUM(amount),0) FROM expenses WHERE strftime('%Y-%m',date)=:m"), {"m": month}).scalar()
        month_data["invested"] = db.execute(text(
            "SELECT IFNULL(SUM(buy_price*quantity),0) FROM portfolio")).scalar()
        cats = db.execute(text(
            "SELECT category, SUM(amount) as total, COUNT(*) as count FROM expenses WHERE strftime('%Y-%m',date)=:m GROUP BY category ORDER BY total DESC"), {"m": month}).fetchall()
        month_data["expense_breakdown"] = [{"category": r[0], "total": float(r[1]), "count": r[2]} for r in cats]
        inc_src = db.execute(text(
            "SELECT source, SUM(amount) as total, COUNT(*) as count FROM income WHERE strftime('%Y-%m',date)=:m GROUP BY source ORDER BY total DESC"), {"m": month}).fetchall()
        month_data["income_breakdown"] = [{"source": r[0], "total": float(r[1]), "count": r[2]} for r in inc_src]
        recent = db.execute(text(
            "SELECT date, category, note, amount FROM expenses WHERE strftime('%Y-%m',date)=:m ORDER BY date DESC LIMIT 10"), {"m": month}).fetchall()
        month_data["recent_expenses"] = [{"date": r[0], "category": r[1], "note": r[2] or "", "amount": float(r[3])} for r in recent]
    except Exception as e:
        from fastapi import HTTPException
        raise HTTPException(status_code=500, detail=str(e))

    month_label = datetime.strptime(month, "%Y-%m").strftime("%B %Y")
    pdf_bytes = generate_monthly_pdf(user, month_data, month_label)
    filename = f"SENRA_Report_{month}.pdf"

    return StreamingResponse(
        io.BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )