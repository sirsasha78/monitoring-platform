from fastapi import FastAPI
from sqlalchemy import text

from app.core.config import settings
from app.core.dependencies import DBSessionDep
from app.modules.auth.handlers import register_auth_exception_handlers
from app.modules.auth.router import router as auth_router

app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    description="Платформа для мониторинга статуса внешних сервисов",
)

app.include_router(auth_router)
register_auth_exception_handlers(app)


@app.get("/health")
async def healthcheck() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/db-check")
async def check_db(session: DBSessionDep) -> dict[str, str]:
    await session.execute(text("SELECT 1"))

    return {"db": "ok"}
