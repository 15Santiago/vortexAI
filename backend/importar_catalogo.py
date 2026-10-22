import csv
import hashlib
import os
from datetime import datetime
from pathlib import Path
from typing import Any

from database import get_db_connection


def _clean(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    if text == "" or text.lower() in {"nan", "none", "null"}:
        return None
    return text


def _parse_float(value: Any) -> float | None:
    cleaned = _clean(value)
    if cleaned is None:
        return None
    try:
        return float(cleaned)
    except ValueError:
        return None


def _parse_int(value: Any) -> int | None:
    numeric = _parse_float(value)
    if numeric is None:
        return None
    return int(numeric)


def _parse_date(value: Any) -> str | None:
    cleaned = _clean(value)
    if cleaned is None:
        return None
    for fmt in ("%Y-%m-%d", "%Y-%m-%d %H:%M:%S", "%Y/%m/%d"):
        try:
            return datetime.strptime(cleaned, fmt).strftime("%Y-%m-%d")
        except ValueError:
            continue
    return cleaned


def _parse_datetime(value: Any) -> str | None:
    cleaned = _clean(value)
    if cleaned is None:
        return None
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
        try:
            return datetime.strptime(cleaned, fmt).strftime("%Y-%m-%d %H:%M:%S")
        except ValueError:
            continue
    return cleaned


def _make_product_key(title: str, category: str, url: str) -> str:
    raw = f"{title.strip()}|{category.strip()}|{(url or '').strip()}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _normalize_category_name(category_name: str | None, title: str | None) -> str:
    category = (category_name or "General").strip() or "General"
    title_text = (title or "").lower()

    battery_keywords = (
        "battery",
        "batteries",
        "power bank",
        "alkaline battery",
        "lithium battery",
        "rechargeable battery",
        "aa battery",
        "aaa battery",
        "9v battery",
        "duracell",
        "energizer",
    )
    charger_keywords = (
        "charger",
        "charging cable",
        "usb-c charger",
        "usb c charger",
        "power adapter",
        "adapter",
        "cable",
    )

    if any(keyword in title_text for keyword in battery_keywords):
        return "Power & Batteries"
    if any(keyword in title_text for keyword in charger_keywords):
        return "Chargers & Cables"
    return category


def _split_sql_statements(sql: str) -> list[str]:
    statements: list[str] = []
    buffer: list[str] = []
    in_single_quote = False
    in_double_quote = False
    i = 0

    while i < len(sql):
        char = sql[i]
        nxt = sql[i + 1] if i + 1 < len(sql) else ""

        if char == "'" and not in_double_quote:
            if in_single_quote and nxt == "'":
                buffer.append(char)
                buffer.append(nxt)
                i += 2
                continue
            in_single_quote = not in_single_quote
            buffer.append(char)
            i += 1
            continue

        if char == '"' and not in_single_quote:
            if in_double_quote and nxt == '"':
                buffer.append(char)
                buffer.append(nxt)
                i += 2
                continue
            in_double_quote = not in_double_quote
            buffer.append(char)
            i += 1
            continue

        if not in_single_quote and not in_double_quote:
            if char == "-" and nxt == "-":
                while i < len(sql) and sql[i] != "\n":
                    i += 1
                continue
            if char == "/" and nxt == "*":
                i += 2
                while i < len(sql) - 1 and not (sql[i] == "*" and sql[i + 1] == "/"):
                    i += 1
                i += 2
                continue
            if char == ";":
                statement = "".join(buffer).strip()
                if statement:
                    statements.append(statement)
                buffer = []
                i += 1
                continue

        buffer.append(char)
        i += 1

    trailing = "".join(buffer).strip()
    if trailing:
        statements.append(trailing)

    return statements


def _ensure_schema(cursor) -> None:
    try:
        cursor.execute("SHOW TABLES")
        if cursor.fetchall():
            return
    except Exception:
        pass

    schema_path = Path(__file__).resolve().parent.parent / "DB" / "schema.sql"
    if not schema_path.exists():
        return

    schema_sql = schema_path.read_text(encoding="utf-8")
    for statement in _split_sql_statements(schema_sql):
        if statement.strip():
            try:
                cursor.execute(statement)
            except Exception as exc:
                if "already exists" not in str(exc).lower():
                    raise


def import_products_from_csv(csv_path: str | None = None) -> dict[str, Any]:
    base_dir = Path(__file__).resolve().parent.parent
    csv_file = Path(csv_path) if csv_path else base_dir / "Data" / "amazon_products_sales_data_cleaned.csv"

    if not csv_file.exists():
        return {"success": False, "message": f"No se encontró el CSV: {csv_file}"}

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    try:
        cursor.execute("CREATE DATABASE IF NOT EXISTS vortexai CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci")
        cursor.execute("USE vortexai")
        _ensure_schema(cursor)

        imported = 0
        with csv_file.open("r", encoding="utf-8", newline="") as file:
            reader = csv.DictReader(file)
            for row in reader:
                title = _clean(row.get("product_title")) or "Sin título"
                category_name = _normalize_category_name(
                    _clean(row.get("product_category")) or "General",
                    title,
                )
                product_url = _clean(row.get("product_page_url")) or ""
                image_url = _clean(row.get("product_image_url")) or ""
                collected_at_raw = _parse_datetime(row.get("data_collected_at"))
                source_key = _make_product_key(title, category_name, product_url)

                cursor.execute(
                    "INSERT INTO categories (name) VALUES (%s) ON DUPLICATE KEY UPDATE name = VALUES(name)",
                    (category_name,),
                )
                cursor.execute("SELECT id FROM categories WHERE name = %s", (category_name,))
                category_id = cursor.fetchone()["id"]

                cursor.execute(
                    """
                    INSERT INTO products (source_key, asin, title, category_id, product_page_url)
                    VALUES (%s, %s, %s, %s, %s)
                    ON DUPLICATE KEY UPDATE
                        title = VALUES(title),
                        category_id = VALUES(category_id),
                        product_page_url = VALUES(product_page_url)
                    """,
                    (source_key, None, title, category_id, product_url),
                )
                cursor.execute("SELECT id FROM products WHERE source_key = %s", (source_key,))
                product_row = cursor.fetchone()
                product_id = product_row["id"]

                if image_url:
                    cursor.execute(
                        """
                        INSERT INTO product_images (product_id, image_url, is_primary)
                        VALUES (%s, %s, TRUE)
                        ON DUPLICATE KEY UPDATE image_url = VALUES(image_url)
                        """,
                        (product_id, image_url),
                    )

                cursor.execute(
                    "DELETE FROM product_observations WHERE product_id = %s AND collected_at = %s",
                    (product_id, collected_at_raw or datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
                )

                cursor.execute(
                    """
                    INSERT INTO product_observations (
                        product_id, collected_at, rating, total_reviews, purchased_last_month,
                        discounted_price, original_price, discount_percentage, seller_badge,
                        is_sponsored, coupon_text, buy_box_availability, delivery_date,
                        sustainability_tag, source_url
                    ) VALUES (
                        %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
                    )
                    """,
                    (
                        product_id,
                        collected_at_raw or datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        _parse_float(row.get("product_rating")),
                        _parse_int(row.get("total_reviews")),
                        _parse_int(row.get("purchased_last_month")),
                        _parse_float(row.get("discounted_price")),
                        _parse_float(row.get("original_price")),
                        _parse_float(row.get("discount_percentage")),
                        _clean(row.get("is_best_seller")),
                        str(_clean(row.get("is_sponsored")) or "").lower() == "sponsored",
                        _clean(row.get("has_coupon")),
                        _clean(row.get("buy_box_availability")),
                        _parse_date(row.get("delivery_date")),
                        _clean(row.get("sustainability_tags")),
                        product_url,
                    ),
                )
                imported += 1

        conn.commit()
        return {"success": True, "message": f"Se importaron {imported} productos a MySQL", "total_imported": imported}
    except Exception as exc:
        conn.rollback()
        return {"success": False, "message": f"Error al importar: {exc}"}
    finally:
        cursor.close()
        conn.close()
