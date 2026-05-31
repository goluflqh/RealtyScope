from fastapi import FastAPI

from realtyscope.config import get_settings

app = FastAPI(
    title="RealtyScope API",
    version="0.1.0",
    description="API skeleton for the RealtyScope grade-5 real estate data service.",
)


@app.get("/health")
def health() -> dict[str, str]:
    settings = get_settings()
    return {
        "service": "realtyscope-api",
        "status": "ok",
        "project": settings.project_name,
        "environment": settings.app_env,
    }
