import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from database import close_pool, get_pool


@asynccontextmanager
async def lifespan(app: FastAPI):
    await get_pool()
    yield
    await close_pool()


app = FastAPI(title="FinanceOS Parser Service", version="0.1.0", lifespan=lifespan)


@app.get("/health")
async def health():
    pool = await get_pool()
    await pool.fetchval("SELECT 1")
    return {"status": "ok", "db": "connected"}
