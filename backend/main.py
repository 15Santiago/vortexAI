import os
from typing import Any

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from database import get_db_connection
from import_csv_to_db import import_products_from_csv

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def home() -> dict[str, Any]:
    return {"status": "OK", "mensaje": "API de vortexAI en línea"}


@app.get("/api/productos")
def obtener_productos() -> dict[str, Any]:
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute(
            """
            SELECT p.id, p.source_key, p.title AS product_title,
                   p.product_page_url,
                   c.name AS product_category,
                   i.image_url AS product_image_url,
                   o.rating AS product_rating,
                   o.total_reviews,
                   o.purchased_last_month,
                   o.discounted_price,
                   o.original_price,
                   o.discount_percentage,
                   o.is_sponsored,
                   o.coupon_text AS has_coupon,
                   o.buy_box_availability,
                   o.delivery_date,
                   o.sustainability_tag AS sustainability_tags,
                   o.collected_at AS data_collected_at,
                   o.source_url
            FROM products p
            LEFT JOIN categories c ON c.id = p.category_id
            LEFT JOIN product_images i ON i.product_id = p.id AND i.is_primary = TRUE
            LEFT JOIN product_observations o ON o.product_id = p.id
            ORDER BY p.id DESC
            """
        )
        rows = cursor.fetchall()
        total = 0
        cursor.execute("SELECT COUNT(*) AS total FROM products")
        total_row = cursor.fetchone()
        if total_row:
            total = int(total_row["total"])
        return {"total": total, "productos": rows}
    except Exception as exc:  # pragma: no cover - fallback for local dev
        return {"error": f"No se pudo consultar la base de datos: {str(exc)}"}


@app.post("/api/importar-datos")
def importar_datos() -> dict[str, Any]:
    try:
        return import_products_from_csv()
    except Exception as exc:  # pragma: no cover
        return {"error": f"Error al importar datos: {str(exc)}"}