import logging
import os
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Any

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from admin_routes import router as admin_router
from auth_routes import router as auth_router
from auth_service import production_mode
from catalog_routes import router as catalog_router


LOG_DIR = Path(__file__).resolve().parent / "logs"
LOG_DIR.mkdir(exist_ok=True)


def _configure_error_logging() -> None:
    handler = RotatingFileHandler(
        LOG_DIR / "errors.log",
        maxBytes=1_000_000,
        backupCount=3,
        encoding="utf-8",
    )
    handler.setLevel(logging.ERROR)
    handler.setFormatter(
        logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s")
    )
    # "" es el logger raíz (errores de nuestras rutas); uvicorn.error captura los fallos no controlados
    for logger_name in ("", "uvicorn.error"):
        target = logging.getLogger(logger_name)
        if not any(isinstance(existing, RotatingFileHandler) for existing in target.handlers):
            target.addHandler(handler)


_configure_error_logging()

app = FastAPI()

allowed_origins = [
    origin.strip()
    for origin in os.getenv(
        "CORS_ORIGINS",
        "http://localhost:5173,http://127.0.0.1:5173",
    ).split(",")
    if origin.strip()
]
if production_mode and any(not origin.startswith("https://") for origin in allowed_origins):
    raise RuntimeError("En producción, CORS_ORIGINS solo puede contener orígenes HTTPS.")

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],  # Permitir todos los métodos evita bloqueos en preflight OPTIONS
    allow_headers=["*"],  # Permitir todas las cabeceras (Authorization, Content-Type, etc.)
)


@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
    if production_mode and request.url.scheme == "https":
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    return response


@app.get("/")
def home() -> dict[str, Any]:
    return {"status": "OK", "mensaje": "API de vortexAI en línea"}


app.include_router(auth_router)
app.include_router(admin_router)
app.include_router(catalog_router)