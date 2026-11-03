"""Backend de mentira SOLO para desarrollo: sirve GET /api/productos leyendo el CSV del proyecto.

Úsalo si no tienes MySQL ni el backend real corriendo:
    python -m uvicorn dev.mock_catalogo:app --port 8000
(el puente lo lee igual que leería el backend de verdad)
"""
import csv
import os
from pathlib import Path

from fastapi import FastAPI

CSV = Path(os.getenv("CATALOGO_CSV", Path(__file__).resolve().parents[2] / "Data" / "amazon_products_sales_data_cleaned.csv"))
LIMITE_POR_CATEGORIA = 600

app = FastAPI()
_productos: list[dict] = []


def _cargar() -> list[dict]:
    vistos: set[str] = set()
    por_categoria: dict[str, int] = {}
    filas = []
    with open(CSV, encoding="utf-8", newline="") as archivo:
        for i, fila in enumerate(csv.DictReader(archivo), start=1):
            titulo, categoria = fila["product_title"], fila["product_category"]
            if titulo in vistos or por_categoria.get(categoria, 0) >= LIMITE_POR_CATEGORIA:
                continue
            vistos.add(titulo)
            por_categoria[categoria] = por_categoria.get(categoria, 0) + 1
            filas.append({
                "id": i, "product_title": titulo, "product_category": categoria,
                "discounted_price": fila["discounted_price"], "original_price": fila["original_price"],
                "discount_percentage": fila["discount_percentage"], "product_rating": fila["product_rating"],
                "total_reviews": fila["total_reviews"], "purchased_last_month": fila["purchased_last_month"],
                "buy_box_availability": fila["buy_box_availability"], "delivery_date": fila["delivery_date"],
            })
    return filas


@app.get("/api/productos")
def productos() -> dict:
    if not _productos:
        _productos.extend(_cargar())
    return {"total": len(_productos), "productos": _productos}
