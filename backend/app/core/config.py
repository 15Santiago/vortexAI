import os


production_mode = os.getenv("APP_ENV", "development").lower() == "production"


def allowed_origins() -> list[str]:
    origins = [
        origin.strip()
        for origin in os.getenv(
            "CORS_ORIGINS",
            "http://localhost:5173,http://127.0.0.1:5173",
        ).split(",")
        if origin.strip()
    ]
    if production_mode and any(not origin.startswith("https://") for origin in origins):
        raise RuntimeError("En producción, CORS_ORIGINS solo puede contener orígenes HTTPS.")
    return origins
