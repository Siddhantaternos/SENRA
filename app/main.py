from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from app.database import engine, Base
from app.routers import expenses, pocket, stocks, insights, income, portfolio, dashboard, agent, auth
from app.routers import nse_live, import_data

Base.metadata.create_all(bind=engine)

app = FastAPI(title="SENRA API", version="3.2.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(expenses.router)
app.include_router(pocket.router)
app.include_router(stocks.router)
app.include_router(nse_live.router)
app.include_router(import_data.router)
app.include_router(insights.router)
app.include_router(income.router)
app.include_router(portfolio.router)
app.include_router(dashboard.router)
app.include_router(agent.router)

@app.get("/")
def serve_frontend():
    return FileResponse("index.html")

@app.get("/health")
def health():
    return {"status": "ok"}