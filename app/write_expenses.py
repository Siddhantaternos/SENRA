content = """from pydantic import BaseModel


class ExpenseCreate(BaseModel):
    date: str
    amount: float
    category: str
    note: str


class ExpenseOut(BaseModel):
    id: int
    date: str
    amount: float
    category: str
    note: str

    class Config:
        from_attributes = True


class IncomeCreate(BaseModel):
    date: str
    amount: float
    source: str
    note: str


class IncomeOut(BaseModel):
    id: int
    date: str
    amount: float
    source: str
    note: str

    class Config:
        from_attributes = True


class PortfolioCreate(BaseModel):
    ticker: str
    buy_price: float
    quantity: float
    date: str
    note: str


class PortfolioOut(BaseModel):
    id: int
    ticker: str
    buy_price: float
    quantity: float
    date: str
    note: str

    class Config:
        from_attributes = True
"""

with open("app/schemas.py", "w") as f:
    f.write(content)

print("Done")