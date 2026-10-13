from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.schemas import HealthResponse

settings = get_settings()

app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    description="Evidence-backed, personalized financial intelligence API.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_url],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health", response_model=HealthResponse, tags=["system"])
async def health_check() -> HealthResponse:
    return HealthResponse(
        status="ok",
        service=settings.app_name,
        environment=settings.app_environment,
    )
