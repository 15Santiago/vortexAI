import re
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from mysql.connector import IntegrityError

from auth_service import (
    AUTH_COOKIE_NAME,
    AccountRequest,
    _create_session,
    _ensure_role_schema,
    _ensure_session_table,
    _hash_password,
    _login_attempt_key,
    _public_user,
    _record_failed_login,
    _secure_cookie_enabled,
    _set_session_cookie,
    _verify_password,
    get_current_user,
    get_optional_current_user,
)
from database import get_db_connection

router = APIRouter()


@router.post("/api/auth/register")
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
        return {
            "user": {
                "id": user_id,
                "full_name": full_name,
                "email": email,
                "is_admin": False,
                "can_view_audit": False,
            }
        }
    except IntegrityError as exc:
        conn.rollback()
        raise HTTPException(status_code=409, detail="Ya existe una cuenta con ese correo.") from exc
    except Exception:
        conn.rollback()
        raise
    finally:
        cursor.close()
        conn.close()


@router.post("/api/auth/login")
def iniciar_sesion(account: AccountRequest, request: Request, response: Response) -> dict[str, Any]:
    identifier = account.email.strip().lower()
    client_ip = request.client.host if request.client else "unknown"
    attempt_key = _login_attempt_key(identifier, client_ip)
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        _ensure_session_table(cursor)
        _ensure_role_schema(cursor)
        conn.commit()
        cursor.execute(
            "SELECT 1 FROM auth_login_attempts WHERE attempt_key = %s AND locked_until > UTC_TIMESTAMP()",
            (attempt_key,),
        )
        if cursor.fetchone():
            raise HTTPException(status_code=429, detail="Demasiados intentos. Espera 15 minutos y vuelve a intentarlo.")

        cursor.execute(
            """
            SELECT u.id, u.full_name, u.email, u.password_hash, u.is_active,
                   u.role_id, r.name AS role_name,
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


@router.get("/api/auth/me")
def obtener_usuario_actual(
    user: dict[str, Any] | None = Depends(get_optional_current_user),
) -> dict[str, Any]:
    return {"user": _public_user(user) if user else None}


@router.post("/api/auth/logout")
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

