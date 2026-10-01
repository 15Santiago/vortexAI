import os

from dotenv import load_dotenv
import mysql.connector
from mysql.connector import Error

load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))


def get_db_connection():
    production = os.getenv("APP_ENV", "development").lower() == "production"
    config = {
        "host": os.getenv("DB_HOST", "localhost"),
        "port": int(os.getenv("DB_PORT", "3306")),
        "user": os.getenv("DB_USER", "root"),
        "password": os.getenv("DB_PASSWORD", ""),
        "charset": "utf8mb4",
        "autocommit": False,
    }

    db_name = os.getenv("DB_NAME")
    if db_name:
        config["database"] = db_name

    if production and config["user"].lower() == "root":
        raise RuntimeError("Configura un usuario MySQL de aplicación con permisos mínimos en producción.")
    if production and not config["password"]:
        raise RuntimeError("DB_PASSWORD es obligatorio en producción.")
    if production and not db_name:
        raise RuntimeError("DB_NAME es obligatorio en producción.")

    ssl_ca = os.getenv("DB_SSL_CA")
    production = os.getenv("APP_ENV", "development").lower() == "production"
    if ssl_ca:
        config.update(
            ssl_ca=ssl_ca,
            ssl_verify_cert=True,
            ssl_verify_identity=True,
        )
    elif production:
        raise RuntimeError("DB_SSL_CA es obligatorio en producción para verificar TLS de MySQL.")

    try:
        return mysql.connector.connect(**config)
    except Error as exc:
        raise RuntimeError("No se pudo conectar a MySQL.") from exc
