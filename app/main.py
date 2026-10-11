from fastapi import FastAPI

app = FastAPI(
    title="monitoring-platform",
    version="0.1.0",
    description="Платформа для мониторинга статуса внешних сервисов",
)


@app.get("/health")
async def healthcheck() -> dict[str, str]:
    return {"status": "ok"}
