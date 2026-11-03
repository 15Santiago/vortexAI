import re
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from mysql.connector import IntegrityError

from app.application.auth_service import (
    AUTH_COOKIE_NAME,
    AUTH_IDLE_MINUTES,
    AccountRequest,
    NAME_PATTERN,
    RegistrationVerificationRequest,
    _validate_password_strength,
    _create_session,
    _ensure_registration_schema,
    _ensure_role_schema,
    _ensure_session_table,
    _get_effective_user_permissions,
    _hash_password,
    _login_attempt_key,
    _public_user,
    _record_failed_login,
    _secure_cookie_enabled,
    send_registration_code,
    _set_session_cookie,
    _verify_password,
    get_current_user,
    get_optional_current_user,
)
from app.infrastructure.database import get_db_connection

router = APIRouter()


@router.post("/api/auth/register")
def registrar_cuenta(account: AccountRequest) -> dict[str, Any]:
    email = account.email.strip().lower()
    full_name = (account.full_name or "").strip()
    if not re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]{2,}", email):
        raise HTTPException(status_code=422, detail="Escribe un correo electrónico válido.")
    if not full_name:
        raise HTTPException(status_code=422, detail="Escribe tu nombre para crear la cuenta.")
    if len(full_name) < 2 or not NAME_PATTERN.fullmatch(full_name):
        raise HTTPException(
            status_code=422,
            detail="Escribe un nombre válido: solo letras, espacios, punto, apóstrofo o guion.",
        )
    _validate_password_strength(account.password)
    
    try:
        conn = get_db_connection()
    except RuntimeError as exc:
        raise HTTPException(
            status_code=503,
            detail="No fue posible conectar con MySQL. Verifica backend/.env y que el servicio MySQL esté activo.",
        ) from exc
    cursor = conn.cursor(dictionary=True)
    try:
        _ensure_registration_schema(cursor)
        _ensure_role_schema(cursor)
        cursor.execute("DELETE FROM registration_verifications WHERE expires_at <= UTC_TIMESTAMP()")
        cursor.execute("SELECT id FROM users WHERE email = %s", (email,))
        if cursor.fetchone():
            raise HTTPException(status_code=409, detail="Ya existe una cuenta con ese correo.")
        cursor.execute(
            "SELECT last_sent_at FROM registration_verifications WHERE email = %s FOR UPDATE",
            (email,),
        )
        pending = cursor.fetchone()
        if pending and pending["last_sent_at"] > datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(seconds=60):
            raise HTTPException(status_code=429, detail="Espera un minuto antes de solicitar otro código.")

        code = f"{secrets.randbelow(1_000_000):06d}"
        code_hash = _hash_password(code)
        cursor.execute(
            """
            INSERT INTO registration_verifications (
                email, full_name, password_hash, code_hash,
                attempts, expires_at, last_sent_at
            ) VALUES (%s, %s, %s, %s, 0,
                      UTC_TIMESTAMP() + INTERVAL 2 MINUTE, UTC_TIMESTAMP())
            ON DUPLICATE KEY UPDATE
                full_name = VALUES(full_name),
                password_hash = VALUES(password_hash),
                code_hash = VALUES(code_hash),
                attempts = 0,
                expires_at = VALUES(expires_at),
                last_sent_at = VALUES(last_sent_at)
            """,
            (email, full_name, _hash_password(account.password), code_hash),
        )
        send_registration_code(email, code)
        conn.commit()
        return {"verification_required": True, "email": email}
    except IntegrityError as exc:
        conn.rollback()
        raise HTTPException(status_code=409, detail="Ya existe una cuenta con ese correo.") from exc
    except Exception:
        conn.rollback()
        raise
    finally:
        cursor.close()
        conn.close()


@router.post("/api/auth/verify-registration")
def verificar_registro(
    payload: RegistrationVerificationRequest,
    response: Response,
) -> dict[str, Any]:
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        _ensure_registration_schema(cursor)
        _ensure_session_table(cursor)
        _ensure_role_schema(cursor)
        cursor.execute(
            """
            SELECT full_name, password_hash, code_hash, attempts, expires_at
            FROM registration_verifications
            WHERE email = %s
            FOR UPDATE
            """,
            (payload.email,),
        )
        pending = cursor.fetchone()
        if not pending:
            raise HTTPException(status_code=400, detail="El código no es válido o ya expiró.")
        if pending["expires_at"] <= datetime.now(timezone.utc).replace(tzinfo=None):
            cursor.execute("DELETE FROM registration_verifications WHERE email = %s", (payload.email,))
            conn.commit()
            raise HTTPException(status_code=400, detail="El código expiró. Solicita uno nuevo.")
        if pending["attempts"] >= 5:
            raise HTTPException(status_code=429, detail="Se agotaron los intentos. Solicita un código nuevo.")

        if not _verify_password(payload.code, pending["code_hash"]):
            cursor.execute(
                "UPDATE registration_verifications SET attempts = attempts + 1 WHERE email = %s",
                (payload.email,),
            )
            conn.commit()
            raise HTTPException(status_code=400, detail="El código de verificación es incorrecto.")

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
            (role_id, payload.email, pending["full_name"], pending["password_hash"]),
        )
        user_id = cursor.lastrowid
        permissions = _get_effective_user_permissions(cursor, user_id, role_id)
        cursor.execute("DELETE FROM registration_verifications WHERE email = %s", (payload.email,))
        token = _create_session(cursor, user_id)
        conn.commit()
        _set_session_cookie(response, token)
        return {
            "user": {
                "id": user_id,
                "full_name": pending["full_name"],
                "email": payload.email,
                "is_admin": False,
                "can_view_audit": False,
                "permissions": permissions,
                "idle_timeout_minutes": AUTH_IDLE_MINUTES,
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
    try:
        conn = get_db_connection()
    except RuntimeError as exc:
        raise HTTPException(
            status_code=503,
            detail="No fue posible conectar con MySQL. Verifica backend/.env y que el servicio MySQL esté activo.",
        ) from exc
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
        user["permissions"] = _get_effective_user_permissions(
            cursor, user["id"], user["role_id"]
        )
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
    response: Response,
    user: dict[str, Any] | None = Depends(get_optional_current_user),
) -> dict[str, Any]:
    if user:
        _set_session_cookie(response, user["session_token"])
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
