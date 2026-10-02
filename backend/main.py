import hashlib
import hmac
import logging
import os
import re
import secrets
import unicodedata
from datetime import datetime, timedelta, timezone
from typing import Any

import bcrypt
from fastapi import Cookie, Depends, FastAPI, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from mysql.connector import IntegrityError
from pydantic import BaseModel, Field, field_validator

from database import get_db_connection
from import_csv_to_db import import_products_from_csv

logger = logging.getLogger(__name__)
app = FastAPI()

allowed_origins = [
    origin.strip()
    for origin in os.getenv(
        "CORS_ORIGINS",
        "http://localhost:5173,http://127.0.0.1:5173",
    ).split(",")
    if origin.strip()
]
production_mode = os.getenv("APP_ENV", "development").lower() == "production"
if production_mode and any(not origin.startswith("https://") for origin in allowed_origins):
    raise RuntimeError("En producción, CORS_ORIGINS solo puede contener orígenes HTTPS.")

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "OPTIONS"],
    allow_headers=["Content-Type"],
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


AUTH_SESSION_DAYS = 7
AUTH_COOKIE_NAME = "vortexai_session"
AUTH_FAILURE_LIMIT = 5


class AccountRequest(BaseModel):
    email: str = Field(min_length=3, max_length=254)
    password: str = Field(min_length=12, max_length=72)
    full_name: str | None = Field(default=None, max_length=150)

    @field_validator("password")
    @classmethod
    def validate_bcrypt_password_length(cls, value: str) -> str:
        if len(value.encode("utf-8")) > 72:
            raise ValueError("La contraseña no puede superar 72 bytes UTF-8.")
        return value


class RoleCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    description: str | None = Field(default=None, max_length=255)

    @field_validator("name")
    @classmethod
    def validate_role_name(cls, value: str) -> str:
        name = value.strip()
        if not name or any(unicodedata.category(character).startswith("C") for character in name):
            raise ValueError("Escribe un nombre de rol válido.")
        return name


class PermissionAssignmentRequest(BaseModel):
    permission_names: list[str] = Field(max_length=50)


class UserRoleAssignmentRequest(BaseModel):
    role_id: int = Field(gt=0)


def _hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt(rounds=12)).decode("ascii")


def _verify_password(password: str, stored_hash: str) -> bool:
    try:
        if stored_hash.startswith(("$2a$", "$2b$", "$2y$")):
            return bcrypt.checkpw(password.encode("utf-8"), stored_hash.encode("ascii"))

        algorithm, salt_hex, digest_hex = stored_hash.split("$", maxsplit=2)
        if algorithm != "scrypt":
            return False
        digest = hashlib.scrypt(
            password.encode("utf-8"),
            salt=bytes.fromhex(salt_hex),
            n=2**14,
            r=8,
            p=1,
            dklen=64,
        )
        return hmac.compare_digest(digest.hex(), digest_hex)
    except (ValueError, TypeError):
        return False


def _ensure_session_table(cursor) -> None:
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS user_sessions (
            token_hash CHAR(64) PRIMARY KEY,
            user_id BIGINT UNSIGNED NOT NULL,
            expires_at DATETIME NOT NULL,
            created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            CONSTRAINT fk_user_sessions_user
                FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE,
            INDEX idx_user_sessions_expiry (expires_at)
        ) ENGINE = InnoDB
        """
    )
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS auth_login_attempts (
            attempt_key CHAR(64) PRIMARY KEY,
            failed_attempts TINYINT UNSIGNED NOT NULL DEFAULT 0,
            window_started_at DATETIME NOT NULL,
            locked_until DATETIME NULL,
            INDEX idx_auth_attempt_lock (locked_until)
        ) ENGINE = InnoDB
        """
    )


def _ensure_role_schema(cursor) -> None:
    cursor.execute(
        """
        SELECT CHARACTER_MAXIMUM_LENGTH
        FROM information_schema.columns
        WHERE table_schema = DATABASE() AND table_name = 'roles' AND column_name = 'name'
        """
    )
    name_column = cursor.fetchone()
    if name_column and name_column["CHARACTER_MAXIMUM_LENGTH"] < 80:
        cursor.execute("ALTER TABLE roles MODIFY COLUMN name VARCHAR(80) NOT NULL")

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS permissions (
            id SMALLINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
            name VARCHAR(80) NOT NULL UNIQUE,
            description VARCHAR(255) NOT NULL
        ) ENGINE = InnoDB
        """
    )
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS role_permissions (
            role_id TINYINT UNSIGNED NOT NULL,
            permission_id SMALLINT UNSIGNED NOT NULL,
            PRIMARY KEY (role_id, permission_id),
            CONSTRAINT fk_role_permissions_role
                FOREIGN KEY (role_id) REFERENCES roles (id) ON DELETE CASCADE,
            CONSTRAINT fk_role_permissions_permission
                FOREIGN KEY (permission_id) REFERENCES permissions (id) ON DELETE CASCADE
        ) ENGINE = InnoDB
        """
    )
    cursor.execute(
        """
        INSERT INTO roles (name, description)
        VALUES ('usuario', 'Acceso general a la aplicación'),
               ('administrador', 'Administración de roles y permisos')
        ON DUPLICATE KEY UPDATE name = VALUES(name)
        """
    )
    permissions = [
        ("catalog.view", "Consultar el catálogo público"),
        ("metrics.view", "Consultar las métricas del catálogo"),
        ("roles.manage", "Crear y consultar roles"),
        ("permissions.manage", "Asignar permisos a roles"),
        ("users.manage", "Consultar usuarios y asignarles roles"),
    ]
    cursor.executemany(
        "INSERT IGNORE INTO permissions (name, description) VALUES (%s, %s)",
        permissions,
    )
    cursor.execute("SELECT COUNT(*) AS total FROM role_permissions")
    if cursor.fetchone()["total"] == 0:
        cursor.execute(
            """
            INSERT IGNORE INTO role_permissions (role_id, permission_id)
            SELECT r.id, p.id
            FROM roles r
            JOIN permissions p ON
                (r.name = 'usuario' AND p.name IN ('catalog.view', 'metrics.view'))
                OR (r.name = 'administrador')
            """
        )


def _create_session(cursor, user_id: int) -> str:
    token = secrets.token_urlsafe(32)
    token_hash = hashlib.sha256(token.encode("utf-8")).hexdigest()
    expires_at = datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(days=AUTH_SESSION_DAYS)
    cursor.execute(
        "INSERT INTO user_sessions (token_hash, user_id, expires_at) VALUES (%s, %s, %s)",
        (token_hash, user_id, expires_at),
    )
    return token


def _login_attempt_key(email: str, client_ip: str) -> str:
    value = f"{email.lower()}|{client_ip}"
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _record_failed_login(cursor, attempt_key: str) -> None:
    cursor.execute(
        """
        INSERT INTO auth_login_attempts (attempt_key, failed_attempts, window_started_at)
        VALUES (%s, 1, UTC_TIMESTAMP())
        ON DUPLICATE KEY UPDATE
            failed_attempts = IF(
                window_started_at < UTC_TIMESTAMP() - INTERVAL 15 MINUTE,
                1,
                failed_attempts + 1
            ),
            locked_until = IF(
                window_started_at < UTC_TIMESTAMP() - INTERVAL 15 MINUTE,
                NULL,
                IF(failed_attempts >= %s, UTC_TIMESTAMP() + INTERVAL 15 MINUTE, locked_until)
            ),
            window_started_at = IF(
                window_started_at < UTC_TIMESTAMP() - INTERVAL 15 MINUTE,
                UTC_TIMESTAMP(),
                window_started_at
            )
        """,
        (attempt_key, AUTH_FAILURE_LIMIT),
    )


def get_current_user(session_cookie: str | None = Cookie(default=None, alias=AUTH_COOKIE_NAME)) -> dict[str, Any]:
    if not session_cookie:
        raise HTTPException(status_code=401, detail="Inicia sesión para consultar las métricas.")

    token = session_cookie.strip()
    if not token:
        raise HTTPException(status_code=401, detail="La sesión no es válida.")

    token_hash = hashlib.sha256(token.encode("utf-8")).hexdigest()
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute(
            """
            SELECT u.id, u.full_name, u.email, u.role_id, r.name AS role_name, s.token_hash
            FROM user_sessions s
            JOIN users u ON u.id = s.user_id
            JOIN roles r ON r.id = u.role_id
            WHERE s.token_hash = %s AND s.expires_at > UTC_TIMESTAMP() AND u.is_active = TRUE
            """,
            (token_hash,),
        )
        user = cursor.fetchone()
        if not user:
            raise HTTPException(status_code=401, detail="La sesión venció. Inicia sesión de nuevo.")
        return user
    finally:
        cursor.close()
        conn.close()


def _public_user(user: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": user["id"],
        "full_name": user["full_name"],
        "email": user["email"],
        "is_admin": user.get("role_name") == "administrador",
    }


def require_permission(permission_name: str):
    def permission_dependency(user: dict[str, Any] = Depends(get_current_user)) -> dict[str, Any]:
        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(
                """
                SELECT 1
                FROM role_permissions rp
                JOIN permissions p ON p.id = rp.permission_id
                WHERE rp.role_id = %s AND p.name = %s
                LIMIT 1
                """,
                (user["role_id"], permission_name),
            )
            if not cursor.fetchone():
                raise HTTPException(status_code=403, detail="No tienes permiso para realizar esta acción.")
            return user
        finally:
            cursor.close()
            conn.close()

    return permission_dependency


def _set_session_cookie(response: Response, token: str) -> None:
    response.set_cookie(
        key=AUTH_COOKIE_NAME,
        value=token,
        max_age=AUTH_SESSION_DAYS * 24 * 60 * 60,
        httponly=True,
        secure=_secure_cookie_enabled(),
        samesite="lax",
        path="/",
    )


def _secure_cookie_enabled() -> bool:
    return (
        os.getenv("AUTH_COOKIE_SECURE", "").lower() == "true"
        or production_mode
    )


@app.get("/")
def home() -> dict[str, Any]:
    return {"status": "OK", "mensaje": "API de vortexAI en línea"}


@app.post("/api/auth/register")
def registrar_cuenta(account: AccountRequest, response: Response) -> dict[str, Any]:
    email = account.email.strip().lower()
    full_name = (account.full_name or "").strip()
    if not re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", email):
        raise HTTPException(status_code=422, detail="Escribe un correo electrónico válido.")
    if not full_name:
        raise HTTPException(status_code=422, detail="Escribe tu nombre para crear la cuenta.")

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        _ensure_session_table(cursor)
        _ensure_role_schema(cursor)
        cursor.execute("SELECT id FROM roles WHERE name = %s", ("usuario",))
        role = cursor.fetchone()
        if not role:
            cursor.execute(
                "INSERT INTO roles (name, description) VALUES (%s, %s)",
                ("usuario", "Puede consultar el catálogo y sus estadísticas"),
            )
            role_id = cursor.lastrowid
        else:
            role_id = role["id"]

        cursor.execute(
            """
            INSERT INTO users (role_id, email, full_name, password_hash)
            VALUES (%s, %s, %s, %s)
            """,
            (role_id, email, full_name, _hash_password(account.password)),
        )
        user_id = cursor.lastrowid
        token = _create_session(cursor, user_id)
        conn.commit()
        _set_session_cookie(response, token)
        return {"user": {"id": user_id, "full_name": full_name, "email": email, "is_admin": False}}
    except IntegrityError as exc:
        conn.rollback()
        raise HTTPException(status_code=409, detail="Ya existe una cuenta con ese correo.") from exc
    except Exception:
        conn.rollback()
        raise
    finally:
        cursor.close()
        conn.close()


@app.post("/api/auth/login")
def iniciar_sesion(account: AccountRequest, request: Request, response: Response) -> dict[str, Any]:
    identifier = account.email.strip().lower()
    client_ip = request.client.host if request.client else "unknown"
    attempt_key = _login_attempt_key(identifier, client_ip)
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        _ensure_session_table(cursor)
        cursor.execute(
            "SELECT 1 FROM auth_login_attempts WHERE attempt_key = %s AND locked_until > UTC_TIMESTAMP()",
            (attempt_key,),
        )
        if cursor.fetchone():
            raise HTTPException(status_code=429, detail="Demasiados intentos. Espera 15 minutos y vuelve a intentarlo.")

        cursor.execute(
            """
            SELECT u.id, u.full_name, u.email, u.password_hash, u.is_active, r.name AS role_name
            FROM users u JOIN roles r ON r.id = u.role_id
            WHERE u.email = %s OR u.username = %s
            """,
            (identifier, identifier),
        )
        user = cursor.fetchone()
        if not user or not user["is_active"] or not _verify_password(account.password, user["password_hash"]):
            _record_failed_login(cursor, attempt_key)
            conn.commit()
            raise HTTPException(status_code=401, detail="Correo o contraseña incorrectos.")

        if not user["password_hash"].startswith(("$2a$", "$2b$", "$2y$")):
            cursor.execute("UPDATE users SET password_hash = %s WHERE id = %s", (_hash_password(account.password), user["id"]))
        cursor.execute("DELETE FROM auth_login_attempts WHERE attempt_key = %s", (attempt_key,))
        cursor.execute("UPDATE users SET last_login_at = UTC_TIMESTAMP() WHERE id = %s", (user["id"],))
        token = _create_session(cursor, user["id"])
        conn.commit()
        _set_session_cookie(response, token)
        return {"user": _public_user(user)}
    except Exception:
        conn.rollback()
        raise
    finally:
        cursor.close()
        conn.close()


@app.get("/api/auth/me")
def obtener_usuario_actual(user: dict[str, Any] = Depends(get_current_user)) -> dict[str, Any]:
    return {"user": _public_user(user)}


@app.post("/api/auth/logout")
def cerrar_sesion(response: Response, user: dict[str, Any] = Depends(get_current_user)) -> dict[str, str]:
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("DELETE FROM user_sessions WHERE token_hash = %s", (user["token_hash"],))
        conn.commit()
        response.delete_cookie(
            key=AUTH_COOKIE_NAME,
            path="/",
            httponly=True,
            secure=_secure_cookie_enabled(),
            samesite="lax",
        )
        return {"message": "Sesión cerrada."}
    finally:
        cursor.close()
        conn.close()


@app.get("/api/admin/permissions")
def listar_permisos(_user: dict[str, Any] = Depends(require_permission("permissions.manage"))) -> dict[str, Any]:
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("SELECT id, name, description FROM permissions ORDER BY name")
        return {"permissions": cursor.fetchall()}
    finally:
        cursor.close()
        conn.close()


@app.get("/api/admin/roles")
def listar_roles(_user: dict[str, Any] = Depends(require_permission("roles.manage"))) -> dict[str, Any]:
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute(
            """
            SELECT r.id, r.name, r.description, COUNT(DISTINCT u.id) AS user_count,
                   GROUP_CONCAT(DISTINCT p.name ORDER BY p.name) AS permission_names
            FROM roles r
            LEFT JOIN users u ON u.role_id = r.id
            LEFT JOIN role_permissions rp ON rp.role_id = r.id
            LEFT JOIN permissions p ON p.id = rp.permission_id
            GROUP BY r.id, r.name, r.description
            ORDER BY r.id
            """
        )
        roles = cursor.fetchall()
        for role in roles:
            role["permission_names"] = role["permission_names"].split(",") if role["permission_names"] else []
        return {"roles": roles}
    finally:
        cursor.close()
        conn.close()


@app.post("/api/admin/roles", status_code=201)
def crear_rol(
    role: RoleCreateRequest,
    _user: dict[str, Any] = Depends(require_permission("roles.manage")),
) -> dict[str, Any]:
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute(
            "INSERT INTO roles (name, description) VALUES (%s, %s)",
            (role.name, role.description.strip() if role.description else None),
        )
        role_id = cursor.lastrowid
        conn.commit()
        return {"role": {"id": role_id, "name": role.name, "description": role.description, "user_count": 0, "permission_names": []}}
    except IntegrityError as exc:
        conn.rollback()
        raise HTTPException(status_code=409, detail="Ya existe un rol con ese identificador.") from exc
    finally:
        cursor.close()
        conn.close()


@app.put("/api/admin/roles/{role_id}/permissions")
def asignar_permisos_a_rol(
    role_id: int,
    assignment: PermissionAssignmentRequest,
    user: dict[str, Any] = Depends(require_permission("permissions.manage")),
) -> dict[str, Any]:
    permission_names = sorted(set(assignment.permission_names))
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("SELECT name FROM roles WHERE id = %s", (role_id,))
        role = cursor.fetchone()
        if not role:
            raise HTTPException(status_code=404, detail="No se encontró el rol.")

        cursor.execute("SELECT name FROM permissions")
        known_permissions = {row["name"] for row in cursor.fetchall()}
        unknown_permissions = set(permission_names) - known_permissions
        if unknown_permissions:
            raise HTTPException(status_code=422, detail="La lista contiene permisos no reconocidos.")

        if role["name"] == "administrador" and not {"roles.manage", "permissions.manage", "users.manage"}.issubset(permission_names):
            raise HTTPException(status_code=422, detail="El rol administrador debe conservar sus permisos de gestión.")
        if user["role_id"] == role_id and not {"roles.manage", "permissions.manage"}.issubset(permission_names):
            raise HTTPException(status_code=422, detail="No puedes quitarte tus permisos de administración.")

        cursor.execute("DELETE FROM role_permissions WHERE role_id = %s", (role_id,))
        if permission_names:
            placeholders = ", ".join(["%s"] * len(permission_names))
            cursor.execute(
                f"SELECT id FROM permissions WHERE name IN ({placeholders})",
                tuple(permission_names),
            )
            permission_ids = [row["id"] for row in cursor.fetchall()]
            cursor.executemany(
                "INSERT INTO role_permissions (role_id, permission_id) VALUES (%s, %s)",
                [(role_id, permission_id) for permission_id in permission_ids],
            )
        conn.commit()
        return {"role_id": role_id, "permission_names": permission_names}
    except Exception:
        conn.rollback()
        raise
    finally:
        cursor.close()
        conn.close()


@app.get("/api/admin/users")
def listar_usuarios(_user: dict[str, Any] = Depends(require_permission("users.manage"))) -> dict[str, Any]:
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute(
            """
            SELECT u.id, u.full_name, u.email, u.is_active, u.created_at,
                   u.role_id, r.name AS role_name
            FROM users u JOIN roles r ON r.id = u.role_id
            ORDER BY u.created_at DESC, u.id DESC
            """
        )
        return {"users": cursor.fetchall()}
    finally:
        cursor.close()
        conn.close()


@app.put("/api/admin/users/{user_id}/role")
def asignar_rol_a_usuario(
    user_id: int,
    assignment: UserRoleAssignmentRequest,
    current_user: dict[str, Any] = Depends(require_permission("users.manage")),
) -> dict[str, str]:
    if user_id == current_user["id"]:
        raise HTTPException(status_code=422, detail="No puedes cambiar tu propio rol.")
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT id FROM roles WHERE id = %s", (assignment.role_id,))
        if not cursor.fetchone():
            raise HTTPException(status_code=404, detail="No se encontró el rol.")
        cursor.execute("SELECT id FROM users WHERE id = %s", (user_id,))
        if not cursor.fetchone():
            raise HTTPException(status_code=404, detail="No se encontró el usuario.")
        cursor.execute("UPDATE users SET role_id = %s WHERE id = %s", (assignment.role_id, user_id))
        conn.commit()
        return {"message": "Rol de usuario actualizado."}
    except Exception:
        conn.rollback()
        raise
    finally:
        cursor.close()
        conn.close()


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
        logger.exception("No se pudo consultar el catálogo")
        raise HTTPException(status_code=503, detail="No se pudo consultar el catálogo.") from exc


@app.get("/api/metricas")
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


@app.post("/api/importar-datos")
def importar_datos() -> dict[str, Any]:
    try:
        return import_products_from_csv()
    except Exception as exc:  # pragma: no cover
        logger.exception("Error al importar datos")
        raise HTTPException(status_code=500, detail="No se pudieron importar los datos.") from exc