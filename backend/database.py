import os

from dotenv import load_dotenv
import mysql.connector
from mysql.connector import Error

load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))


def get_db_connection():
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

    try:
        return mysql.connector.connect(**config)
    except Error:
        if "database" not in config:
            raise

        fallback = dict(config)
        fallback.pop("database", None)
        try:
            return mysql.connector.connect(**fallback)
        except Error as exc:
            raise RuntimeError(f"No se pudo conectar a MySQL: {exc}") from exc
