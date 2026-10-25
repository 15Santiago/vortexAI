import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException

from auth_service import get_current_user, require_permission
from database import get_db_connection
from importar_catalogo import import_products_from_csv

logger = logging.getLogger(__name__)
router = APIRouter()

# Máximo de productos que se muestran por categoría (15 categorías x 600 = ~9.000)
LIMITE_POR_CATEGORIA = 600


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
            JOIN (
                SELECT id FROM (
                    SELECT id,
                           ROW_NUMBER() OVER (PARTITION BY category_id ORDER BY id DESC) AS rn
                    FROM (
                        SELECT id, category_id,
                               ROW_NUMBER() OVER (PARTITION BY title ORDER BY id DESC) AS title_rank
                        FROM products
                    ) unique_titles
                    WHERE title_rank = 1
                ) ranked
                WHERE rn <= %s
            ) keep ON keep.id = p.id
            LEFT JOIN categories c ON c.id = p.category_id
            LEFT JOIN (
                SELECT product_id, image_url,
                       ROW_NUMBER() OVER (PARTITION BY product_id ORDER BY image_url) AS rn
                FROM product_images
                WHERE is_primary = TRUE
            ) i ON i.product_id = p.id AND i.rn = 1
            LEFT JOIN (
                SELECT product_id, rating, total_reviews, purchased_last_month,
                       discounted_price, original_price, discount_percentage,
                       is_sponsored, coupon_text, buy_box_availability, delivery_date,
                       sustainability_tag, collected_at, source_url,
                       ROW_NUMBER() OVER (
                           PARTITION BY product_id
                           ORDER BY collected_at DESC, id DESC
                       ) AS rn
                FROM product_observations
            ) o ON o.product_id = p.id AND o.rn = 1
            ORDER BY p.id DESC
            """,
            (LIMITE_POR_CATEGORIA,),
        )
        rows = cursor.fetchall()
        return {"total": len(rows), "productos": rows}
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


# ---------------------------------------------------------------------------
# Módulo de sugerencias: historial del usuario + modelo de recomendación
# ---------------------------------------------------------------------------

_history_table_ready = False


def _ensure_history_table(cursor) -> None:
    global _history_table_ready
    if _history_table_ready:
        return
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS user_product_views (
            id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
            user_id BIGINT UNSIGNED NOT NULL,
            product_id BIGINT UNSIGNED NOT NULL,
            viewed_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            CONSTRAINT fk_views_user
                FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE,
            INDEX idx_views_user (user_id, viewed_at)
        ) ENGINE = InnoDB
        """
    )
    _history_table_ready = True


def _normalize_title(value: str | None) -> str:
    return " ".join((value or "").lower().split())


def _fetch_product_cards(cursor, product_ids: list[int]) -> list[dict[str, Any]]:
    cards: list[dict[str, Any]] = []
    for product_id in product_ids:
        cursor.execute(
            """
            SELECT p.id, p.source_key, p.title AS product_title,
                   p.product_page_url,
                   c.name AS product_category,
                   i.image_url AS product_image_url,
                   o.rating AS product_rating,
                   o.total_reviews,
                   o.discounted_price,
                   o.original_price
            FROM products p
            LEFT JOIN categories c ON c.id = p.category_id
            LEFT JOIN product_images i ON i.product_id = p.id AND i.is_primary = TRUE
            LEFT JOIN product_observations o ON o.product_id = p.id
            WHERE p.id = %s
            LIMIT 1
            """,
            (product_id,),
        )
        row = cursor.fetchone()
        if row:
            cards.append(row)
    return cards


def _most_reviewed_ids(cursor, limit: int, exclude: set[int]) -> list[int]:
    cursor.execute(
        """
        SELECT o.product_id, p.title
        FROM product_observations o
        JOIN products p ON p.id = o.product_id
        WHERE o.total_reviews IS NOT NULL
        GROUP BY o.product_id, p.title
        ORDER BY MAX(o.total_reviews) DESC
        LIMIT %s
        """,
        (limit * 5 + len(exclude),),
    )
    ids: list[int] = []
    seen_titles: set[str] = set()
    for row in cursor.fetchall():
        product_id = int(row["product_id"])
        title_key = _normalize_title(row["title"])
        if product_id in exclude or title_key in seen_titles:
            continue
        seen_titles.add(title_key)
        ids.append(product_id)
        if len(ids) >= limit:
            break
    return ids


@router.post("/api/historial/{product_id}")
def registrar_vista(
    product_id: int,
    user: dict[str, Any] = Depends(get_current_user),
) -> dict[str, bool]:
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        _ensure_history_table(cursor)
        cursor.execute("SELECT id FROM products WHERE id = %s", (product_id,))
        if not cursor.fetchone():
            raise HTTPException(status_code=404, detail="No se encontró el producto.")

        # Evita guardar la misma visita dos veces seguidas (React ejecuta efectos dos veces en desarrollo)
        cursor.execute(
            """
            SELECT 1 FROM user_product_views
            WHERE user_id = %s AND product_id = %s
              AND viewed_at > (NOW() - INTERVAL 30 SECOND)
            LIMIT 1
            """,
            (user["id"], product_id),
        )
        if cursor.fetchone():
            return {"ok": True}

        cursor.execute(
            "INSERT INTO user_product_views (user_id, product_id) VALUES (%s, %s)",
            (user["id"], product_id),
        )
        conn.commit()
        return {"ok": True}
    except HTTPException:
        raise
    except Exception as exc:
        conn.rollback()
        logger.exception("No se pudo registrar la vista del producto %s", product_id)
        raise HTTPException(status_code=503, detail="No se pudo registrar la vista.") from exc
    finally:
        cursor.close()
        conn.close()


@router.get("/api/recomendaciones")
def obtener_recomendaciones(user: dict[str, Any] = Depends(get_current_user)) -> dict[str, Any]:
    limit = 8
    recent_limit = 6  # solo cuentan las últimas visitas distintas
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        _ensure_history_table(cursor)
        cursor.execute(
            """
            SELECT product_id, MAX(viewed_at) AS last_view
            FROM user_product_views
            WHERE user_id = %s
            GROUP BY product_id
            ORDER BY last_view DESC
            LIMIT %s
            """,
            (user["id"], recent_limit),
        )
        viewed_ids = [int(row["product_id"]) for row in cursor.fetchall()]  # de más reciente a más antigua

        # Usuario sin historial: se muestran los productos con más reseñas
        if not viewed_ids:
            ids = _most_reviewed_ids(cursor, limit, set())
            return {"modo": "populares", "productos": _fetch_product_cards(cursor, ids)}

        id_placeholders = ", ".join(["%s"] * len(viewed_ids))
        cursor.execute(
            f"""
            SELECT p.id, p.title, p.category_id, c.name AS category
            FROM products p
            LEFT JOIN categories c ON c.id = p.category_id
            WHERE p.id IN ({id_placeholders})
            """,
            tuple(viewed_ids),
        )
        rows_by_id = {int(row["id"]): row for row in cursor.fetchall()}
        viewed_rows = [rows_by_id[product_id] for product_id in viewed_ids if product_id in rows_by_id]

        category_ids = sorted({row["category_id"] for row in viewed_rows if row["category_id"] is not None})
        pool: list[dict[str, Any]] = []
        if category_ids:
            category_placeholders = ", ".join(["%s"] * len(category_ids))
            cursor.execute(
                f"""
                SELECT id, title, category FROM (
                    SELECT p.id, p.title, c.name AS category,
                           ROW_NUMBER() OVER (PARTITION BY p.category_id ORDER BY p.id DESC) AS rn
                    FROM products p
                    LEFT JOIN categories c ON c.id = p.category_id
                    WHERE p.category_id IN ({category_placeholders})
                ) per_category
                WHERE rn <= 1500
                """,
                tuple(category_ids),
            )
            viewed_set = set(viewed_ids)
            pool = [row for row in cursor.fetchall() if row["id"] not in viewed_set]

        if not pool or not viewed_rows:
            ids = _most_reviewed_ids(cursor, limit, set(viewed_ids))
            return {"modo": "populares", "productos": _fetch_product_cards(cursor, ids)}

        # Modelo de recomendación por contenido: TF-IDF + similitud coseno
        import numpy as np
        from sklearn.feature_extraction.text import TfidfVectorizer
        from sklearn.metrics.pairwise import linear_kernel

        def as_text(row: dict[str, Any]) -> str:
            return f"{row['title'] or ''} {row['category'] or ''}"

        def title_key(value: str | None) -> str:
            # Primeras palabras del título: agrupa variantes casi idénticas del mismo producto
            return " ".join(_normalize_title(value).split()[:6])

        vectorizer = TfidfVectorizer(stop_words="english", max_features=5000)
        matrix = vectorizer.fit_transform(
            [as_text(row) for row in viewed_rows] + [as_text(row) for row in pool]
        )
        viewed_matrix = matrix[: len(viewed_rows)]
        pool_matrix = matrix[len(viewed_rows):]

        # Las visitas más recientes pesan más (cada visita anterior pesa 85% de la siguiente)
        weights = np.array([0.85 ** position for position in range(len(viewed_rows))])
        similarity = (linear_kernel(viewed_matrix, pool_matrix) * weights[:, None]).max(axis=0)

        ranked = sorted(range(len(pool)), key=lambda index: float(similarity[index]), reverse=True)

        # No sugerir copias de lo que ya viste ni variantes del mismo producto
        seen_titles = {title_key(row["title"]) for row in viewed_rows}
        ids: list[int] = []
        for index in ranked:
            key = title_key(pool[index]["title"])
            if key in seen_titles:
                continue
            seen_titles.add(key)
            ids.append(int(pool[index]["id"]))
            if len(ids) >= limit:
                break

        return {"modo": "historial", "productos": _fetch_product_cards(cursor, ids)}
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("No se pudieron calcular las recomendaciones")
        raise HTTPException(status_code=503, detail="No se pudieron calcular las recomendaciones.") from exc
    finally:
        cursor.close()
        conn.close()