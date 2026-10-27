import hashlib
import hmac
import json
import os
import re
import secrets
import threading
import unicodedata
from datetime import datetime, timedelta, timezone
from typing import Any

import bcrypt
from fastapi import Cookie, Depends, HTTPException, Request, Response
from pydantic import BaseModel, Field, field_validator

from database import get_db_connection

production_mode = os.getenv("APP_ENV", "development").lower() == "production"


AUTH_SESSION_DAYS = 7
AUTH_COOKIE_NAME = "vortexai_session"
AUTH_FAILURE_LIMIT = 5
AUTH_IDLE_MINUTES = max(1, int(os.getenv("AUTH_IDLE_MINUTES", "30")))
_session_activity_column_ready = False
_audit_log_table_ready = False
_audit_log_table_lock = threading.Lock()
_user_permission_schema_ready = False
_user_permission_schema_lock = threading.Lock()


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
    permission_names: list[str] = Field(default_factory=list, max_length=50)
    staff_full_name: str = Field(min_length=1, max_length=150)
    staff_email: str = Field(min_length=3, max_length=254)
    staff_username: str = Field(min_length=3, max_length=50)
    staff_password: str = Field(min_length=12, max_length=72)

    @field_validator("name")
    @classmethod
    def validate_role_name(cls, value: str) -> str:
        name = value.strip()
        if not name or any(unicodedata.category(character).startswith("C") for character in name):
            raise ValueError("Escribe un nombre de rol válido.")
        return name

    @field_validator("staff_password")
    @classmethod
    def validate_staff_password_length(cls, value: str) -> str:
        if len(value.encode("utf-8")) > 72:
            raise ValueError("La contraseña no puede superar 72 bytes UTF-8.")
        return value

    @field_validator("staff_email")
    @classmethod
    def validate_staff_email(cls, value: str) -> str:
        email = value.strip().lower()
        if not re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", email):
            raise ValueError("Escribe un correo electrónico válido para el personal.")
        return email

    @field_validator("staff_full_name", "staff_username")
    @classmethod
    def normalize_staff_identity(cls, value: str, info) -> str:
        normalized = value.strip()
        if not normalized or any(unicodedata.category(character).startswith("C") for character in normalized):
            raise ValueError("Completa los datos de acceso del personal con valores válidos.")
        return normalized.lower() if info.field_name == "staff_username" else normalized


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
    global _session_activity_column_ready
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS user_sessions (
            token_hash CHAR(64) PRIMARY KEY,
            user_id BIGINT UNSIGNED NOT NULL,
            expires_at DATETIME NOT NULL,
            created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            last_activity_at DATETIME NULL,
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
    if not _session_activity_column_ready:
        cursor.execute(
            """
            SELECT COUNT(*) AS total
            FROM information_schema.columns
            WHERE table_schema = DATABASE()
              AND table_name = 'user_sessions'
              AND column_name = 'last_activity_at'
            """
        )
        if cursor.fetchone()["total"] == 0:
            cursor.execute("ALTER TABLE user_sessions ADD COLUMN last_activity_at DATETIME NULL")
        _session_activity_column_ready = True

def _ensure_audit_log_table(cursor) -> None:
    global _audit_log_table_ready
    if _audit_log_table_ready:
        return

    with _audit_log_table_lock:
        if _audit_log_table_ready:
            return
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS audit_logs (
                id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
                actor_user_id BIGINT UNSIGNED NULL,
                actor_name VARCHAR(150) NOT NULL,
                actor_email VARCHAR(254) NOT NULL,
                action VARCHAR(100) NOT NULL,
                entity_type VARCHAR(50) NOT NULL,
                entity_id VARCHAR(100) NULL,
                old_values JSON NULL,
                new_values JSON NULL,
                ip_address VARCHAR(45) NULL,
                user_agent VARCHAR(512) NULL,
                created_at DATETIME(6) NOT NULL DEFAULT (UTC_TIMESTAMP(6)),
                CONSTRAINT fk_audit_logs_actor
                    FOREIGN KEY (actor_user_id) REFERENCES users (id) ON DELETE SET NULL,
                INDEX idx_audit_logs_created_at (created_at),
                INDEX idx_audit_logs_actor_created_at (actor_user_id, created_at),
                INDEX idx_audit_logs_entity (entity_type, entity_id)
            ) ENGINE = InnoDB
            """
        )
        _audit_log_table_ready = True


def _ensure_user_permission_schema(cursor) -> None:
    global _user_permission_schema_ready
    if _user_permission_schema_ready:
        return

    with _user_permission_schema_lock:
        if _user_permission_schema_ready:
            return
        cursor.execute(
            """
            INSERT IGNORE INTO permissions (name, description)
            VALUES ('audit.view', 'Consultar los registros de auditoría')
            """
        )
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS user_permissions (
                user_id BIGINT UNSIGNED NOT NULL,
                permission_id SMALLINT UNSIGNED NOT NULL,
                is_granted BOOLEAN NOT NULL,
                PRIMARY KEY (user_id, permission_id),
                CONSTRAINT fk_user_permissions_user
                    FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE,
                CONSTRAINT fk_user_permissions_permission
                    FOREIGN KEY (permission_id) REFERENCES permissions (id) ON DELETE CASCADE
            ) ENGINE = InnoDB
            """
        )
        cursor.execute(
            """
            INSERT IGNORE INTO role_permissions (role_id, permission_id)
            SELECT r.id, p.id
            FROM roles r
            JOIN permissions p ON p.name = 'audit.view'
            WHERE r.name = 'administrador'
            """
        )
        _user_permission_schema_ready = True


def _get_effective_user_permissions(cursor, user_id: int, role_id: int) -> list[str]:
    cursor.execute(
        """
        SELECT p.name
        FROM permissions p
        LEFT JOIN role_permissions rp
            ON rp.permission_id = p.id AND rp.role_id = %s
        LEFT JOIN user_permissions up
            ON up.permission_id = p.id AND up.user_id = %s
        WHERE (up.user_id IS NOT NULL AND up.is_granted = TRUE)
           OR (up.user_id IS NULL AND rp.role_id IS NOT NULL)
        ORDER BY p.name
        """,
        (role_id, user_id),
    )
    return [row["name"] for row in cursor.fetchall()]


def _write_audit_log(
    cursor,
    request: Request,
    actor: dict[str, Any],
    action: str,
    entity_type: str,
    entity_id: int | str,
    old_values: dict[str, Any] | None = None,
    new_values: dict[str, Any] | None = None,
) -> None:
    client_ip = request.client.host if request.client else None
    cursor.execute(
        """
        INSERT INTO audit_logs (
            actor_user_id, actor_name, actor_email, action, entity_type, entity_id,
            old_values, new_values, ip_address, user_agent, created_at
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, UTC_TIMESTAMP(6))
        """,
        (
            actor["id"],
            actor["full_name"],
            actor["email"],
            action,
            entity_type,
            str(entity_id),
            json.dumps(old_values, ensure_ascii=False) if old_values is not None else None,
            json.dumps(new_values, ensure_ascii=False) if new_values is not None else None,
            client_ip,
            request.headers.get("user-agent", "")[:512] or None,
        ),
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
        ("audit.view", "Consultar los registros de auditoría"),
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
    _ensure_user_permission_schema(cursor)


def _create_session(cursor, user_id: int) -> str:
    token = secrets.token_urlsafe(32)
    token_hash = hashlib.sha256(token.encode("utf-8")).hexdigest()
    expires_at = datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(days=AUTH_SESSION_DAYS)
    cursor.execute(
        """
        INSERT INTO user_sessions (token_hash, user_id, expires_at, last_activity_at)
        VALUES (%s, %s, %s, UTC_TIMESTAMP())
        """,
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
        _ensure_session_table(cursor)
        _ensure_user_permission_schema(cursor)
        conn.commit()
        cursor.execute(
            """
            SELECT u.id, u.full_name, u.email, u.role_id, r.name AS role_name, s.token_hash,
                   EXISTS (
                       SELECT 1
                       FROM permissions p
                       LEFT JOIN role_permissions rp
                           ON rp.permission_id = p.id AND rp.role_id = u.role_id
                       LEFT JOIN user_permissions up
                           ON up.permission_id = p.id AND up.user_id = u.id
                       WHERE p.name = 'audit.view'
                         AND (
                             (up.user_id IS NOT NULL AND up.is_granted = TRUE)
                             OR (up.user_id IS NULL AND rp.role_id IS NOT NULL)
                         )
                   ) AS can_view_audit
            FROM user_sessions s
            JOIN users u ON u.id = s.user_id
            JOIN roles r ON r.id = u.role_id
            WHERE s.token_hash = %s
              AND s.expires_at > UTC_TIMESTAMP()
              AND u.is_active = TRUE
              AND (
                  s.last_activity_at IS NULL
                  OR s.last_activity_at > UTC_TIMESTAMP() - INTERVAL %s MINUTE
              )
            """,
            (token_hash, AUTH_IDLE_MINUTES),
        )
        user = cursor.fetchone()
        if not user:
            raise HTTPException(
                status_code=401,
                detail="La sesión venció por inactividad o ya no es válida. Inicia sesión de nuevo.",
            )
        cursor.execute(
            "UPDATE user_sessions SET last_activity_at = UTC_TIMESTAMP() WHERE token_hash = %s",
            (token_hash,),
        )
        conn.commit()
        return user
    finally:
        cursor.close()
        conn.close()


def get_optional_current_user(
    session_cookie: str | None = Cookie(default=None, alias=AUTH_COOKIE_NAME),
) -> dict[str, Any] | None:
    try:
        return get_current_user(session_cookie)
    except HTTPException as exc:
        if exc.status_code == 401:
            return None
        raise


def _public_user(user: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": user["id"],
        "full_name": user["full_name"],
        "email": user["email"],
        "is_admin": user.get("role_name") == "administrador",
        "can_view_audit": bool(user.get("can_view_audit", False)),
    }


def require_permission(permission_name: str):
    def permission_dependency(user: dict[str, Any] = Depends(get_current_user)) -> dict[str, Any]:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        try:
            _ensure_user_permission_schema(cursor)
            conn.commit()
            cursor.execute(
                """
                SELECT EXISTS (
                    SELECT 1
                    FROM user_permissions up
                    JOIN permissions p ON p.id = up.permission_id
                    WHERE up.user_id = %s AND p.name = %s AND up.is_granted = TRUE
                ) OR (
                    NOT EXISTS (
                        SELECT 1
                        FROM user_permissions up
                        JOIN permissions p ON p.id = up.permission_id
                        WHERE up.user_id = %s AND p.name = %s
                    )
                    AND EXISTS (
                        SELECT 1
                        FROM role_permissions rp
                        JOIN permissions p ON p.id = rp.permission_id
                        WHERE rp.role_id = %s AND p.name = %s
                    )
                ) AS permitted
                LIMIT 1
                """,
                (
                    user["id"], permission_name,
                    user["id"], permission_name,
                    user["role_id"], permission_name,
                ),
            )
            if not cursor.fetchone()["permitted"]:
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

NAME_PATTERN = re.compile(r"^[^\W\d_]+(?:[ '.\-][^\W\d_]+)*$")


def _validate_password_strength(password: str) -> None:
    if any(character.isspace() for character in password):
        raise HTTPException(status_code=422, detail="La contraseña no puede tener espacios.")
    if not any(character.isupper() for character in password):
        raise HTTPException(status_code=422, detail="La contraseña debe incluir una letra mayúscula.")
    if not any(character.islower() for character in password):
        raise HTTPException(status_code=422, detail="La contraseña debe incluir una letra minúscula.")
    if not any(character.isdigit() for character in password):
        raise HTTPException(status_code=422, detail="La contraseña debe incluir un número.")
    if not any(not character.isalnum() and not character.isspace() for character in password):
        raise HTTPException(status_code=422, detail="La contraseña debe incluir un símbolo (por ejemplo ! @ # $ %).")