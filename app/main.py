from fastapi import FastAPI
from sqlalchemy import text

from app.core.config import settings
from app.core.dependencies import DBSessionDep

app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    description="Платформа для мониторинга статуса внешних сервисов",
)


@app.get("/health")
async def healthcheck() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/db-check")
async def check_db(session: DBSessionDep) -> dict[str, str]:
    await session.execute(text("SELECT 1"))

    return {"db": "ok"}
