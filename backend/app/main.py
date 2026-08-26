"""FastAPI 应用入口：注册路由、CORS、启动时初始化数据库。"""
from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import settings
from .database import SessionLocal
from .routers import blacklists, cases, dashboard, risk
from .seed import create_tables, seed_all


@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        create_tables()
        db = SessionLocal()
        try:
            seed_all(db)
        finally:
            db.close()
        print("数据库初始化（建表 + 种子数据）完成。")
    except Exception as exc:  # pragma: no cover - 依赖数据库可用
        print("数据库初始化失败，请确认 MySQL 已启动：", exc)
    yield


app = FastAPI(title=settings.app_name, version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(risk.router, prefix="/api/risk", tags=["风险检查与规则管理"])
app.include_router(cases.router, prefix="/api/risk", tags=["案件审核"])
app.include_router(blacklists.router, prefix="/api/risk", tags=["黑名单"])
app.include_router(dashboard.router, prefix="/api/risk", tags=["用户画像与运营看板"])


@app.get("/api/health", tags=["系统"])
def health():
    return {"status": "ok", "service": settings.app_name}
