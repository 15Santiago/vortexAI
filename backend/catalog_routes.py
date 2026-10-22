import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException

from auth_service import get_current_user, require_permission
from database import get_db_connection
from importar_catalogo import import_products_from_csv

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/api/productos")
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
        logger.exception("No se pudo consultar el catálogo")
        raise HTTPException(status_code=503, detail="No se pudo consultar el catálogo.") from exc


@router.get("/api/metricas")
def obtener_metricas(_user: dict[str, Any] = Depends(require_permission("metrics.view"))) -> dict[str, Any]:
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute(
            """
            SELECT p.id, p.title AS product_title, c.name AS product_category,
                   latest.rating AS product_rating,
                   latest.total_reviews,
                   latest.discounted_price,
                   latest.original_price
            FROM products p
            LEFT JOIN categories c ON c.id = p.category_id
            LEFT JOIN (
                SELECT product_id, rating, total_reviews, discounted_price, original_price,
                       ROW_NUMBER() OVER (
                           PARTITION BY product_id
                           ORDER BY collected_at DESC, id DESC
                       ) AS observation_rank
                FROM product_observations
            ) latest ON latest.product_id = p.id AND latest.observation_rank = 1
            ORDER BY p.id DESC
            """
        )
        products = cursor.fetchall()
        cursor.close()
        conn.close()


        category_totals: dict[str, dict[str, Any]] = {}
        price_buckets = {"Menos de $25": 0, "$25 a $100": 0, "$100 a $500": 0, "$500 o más": 0}
        ratings: list[float] = []
        prices: list[float] = []
        total_reviews = 0

        for product in products:
            category_name = product["product_category"] or "Sin categoría"
            category = category_totals.setdefault(
                category_name,
                {"name": category_name, "product_count": 0, "rating_sum": 0.0, "rating_count": 0, "price_sum": 0.0, "price_count": 0},
            )
            category["product_count"] += 1

            rating = product["product_rating"]
            if rating is not None:
                rating_value = float(rating)
                ratings.append(rating_value)
                category["rating_sum"] += rating_value
                category["rating_count"] += 1

            reviews = int(product["total_reviews"] or 0)
            total_reviews += reviews

            price = product["discounted_price"] or product["original_price"]
            if price is not None:
                price_value = float(price)
                prices.append(price_value)
                category["price_sum"] += price_value
                category["price_count"] += 1
                if price_value < 25:
                    price_buckets["Menos de $25"] += 1
                elif price_value < 100:
                    price_buckets["$25 a $100"] += 1
                elif price_value < 500:
                    price_buckets["$100 a $500"] += 1
                else:
                    price_buckets["$500 o más"] += 1

        categories = []
        for category in category_totals.values():
            rating_count = category.pop("rating_count")
            rating_sum = category.pop("rating_sum")
            price_count = category.pop("price_count")
            price_sum = category.pop("price_sum")
            category["average_rating"] = round(rating_sum / rating_count, 2) if rating_count else None
            category["average_price"] = round(price_sum / price_count, 2) if price_count else None
            category["share_percent"] = round(category["product_count"] / len(products) * 100, 1) if products else 0
            categories.append(category)
        categories.sort(key=lambda item: item["product_count"], reverse=True)

        top_products = sorted(
            (product for product in products if product["total_reviews"]),
            key=lambda product: int(product["total_reviews"] or 0),
            reverse=True,
        )[:5]

        return {
            "total_products": len(products),
            "total_categories": len(categories),
            "average_rating": round(sum(ratings) / len(ratings), 2) if ratings else None,
            "total_reviews": total_reviews,
            "average_price": round(sum(prices) / len(prices), 2) if prices else None,
            "categories": categories,
            "price_distribution": [
                {"label": label, "product_count": count}
                for label, count in price_buckets.items()
            ],
            "top_products": top_products,
        }
    except Exception as exc:  # pragma: no cover - fallback for local dev
        logger.exception("No se pudieron consultar las métricas")
        raise HTTPException(status_code=503, detail="No se pudieron consultar las métricas.") from exc


@router.get("/api/productos/{product_id}")
def obtener_producto(
    product_id: int,
    _user: dict[str, Any] = Depends(get_current_user),
) -> dict[str, Any]:
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
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
            WHERE p.id = %s
            LIMIT 1
            """,
            (product_id,),
        )
        product = cursor.fetchone()
        if not product:
            raise HTTPException(status_code=404, detail="No se encontró el producto.")
        return {"producto": product}
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("No se pudo consultar el detalle del producto %s", product_id)
        raise HTTPException(status_code=503, detail="No se pudo consultar el producto.") from exc
    finally:
        cursor.close()
        conn.close()


@router.post("/api/importar-datos")
def importar_datos() -> dict[str, Any]:
    try:
        return import_products_from_csv()
    except Exception as exc:  # pragma: no cover
        logger.exception("Error al importar datos")
        raise HTTPException(status_code=500, detail="No se pudieron importar los datos.") from exc