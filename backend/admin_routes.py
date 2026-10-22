from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request
from mysql.connector import IntegrityError

from auth_service import (
    PermissionAssignmentRequest,
    RoleCreateRequest,
    UserRoleAssignmentRequest,
    _ensure_audit_log_table,
    _ensure_user_permission_schema,
    _get_effective_user_permissions,
    _hash_password,
    _write_audit_log,
    require_permission,
)
from database import get_db_connection

router = APIRouter()


@router.get("/api/admin/permissions")
def listar_permisos(_user: dict[str, Any] = Depends(require_permission("users.manage"))) -> dict[str, Any]:
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("SELECT id, name, description FROM permissions ORDER BY name")
        return {"permissions": cursor.fetchall()}
    finally:
        cursor.close()
        conn.close()


@router.get("/api/admin/roles")
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


@router.post("/api/admin/roles", status_code=201)
def crear_rol(
    role: RoleCreateRequest,
    request: Request,
    _user: dict[str, Any] = Depends(require_permission("roles.manage")),
) -> dict[str, Any]:
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        _ensure_user_permission_schema(cursor)
        _ensure_audit_log_table(cursor)
        cursor.execute("SELECT id, name FROM permissions")
        permission_ids = {row["name"]: row["id"] for row in cursor.fetchall()}
        permission_names = sorted(set(role.permission_names))
        if set(permission_names) - permission_ids.keys():
            raise HTTPException(status_code=422, detail="La lista contiene permisos no reconocidos.")

        cursor.execute(
            "INSERT INTO roles (name, description) VALUES (%s, %s)",
            (role.name, role.description.strip() if role.description else None),
        )
        role_id = cursor.lastrowid
        cursor.execute(
            """
            INSERT INTO users (role_id, email, full_name, username, password_hash)
            VALUES (%s, %s, %s, %s, %s)
            """,
            (
                role_id,
                role.staff_email,
                role.staff_full_name,
                role.staff_username,
                _hash_password(role.staff_password),
            ),
        )
        user_id = cursor.lastrowid
        if permission_names:
            cursor.executemany(
                """
                INSERT INTO user_permissions (user_id, permission_id, is_granted)
                VALUES (%s, %s, TRUE)
                """,
                [(user_id, permission_ids[name]) for name in permission_names],
            )
        cursor.execute(
            """
            SELECT u.id, u.full_name, u.email, u.username, u.is_active, u.created_at,
                   u.role_id, r.name AS role_name
            FROM users u JOIN roles r ON r.id = u.role_id
            WHERE u.id = %s
            """,
            (user_id,),
        )
        created_user = cursor.fetchone()
        _write_audit_log(
            cursor,
            request,
            _user,
            "role.create",
            "role",
            role_id,
            new_values={
                "name": role.name,
                "description": role.description.strip() if role.description else None,
                "staff_account": {
                    "id": user_id,
                    "full_name": role.staff_full_name,
                    "email": role.staff_email,
                    "username": role.staff_username,
                    "permission_names": permission_names,
                },
            },
        )
        conn.commit()
        return {
            "role": {"id": role_id, "name": role.name, "description": role.description, "user_count": 1, "permission_names": []},
            "user": created_user,
        }
    except IntegrityError as exc:
        conn.rollback()
        raise HTTPException(status_code=409, detail="El rol, correo o usuario ya existe.") from exc
    except Exception:
        conn.rollback()
        raise
    finally:
        cursor.close()
        conn.close()


@router.get("/api/admin/users")
def listar_usuarios(_user: dict[str, Any] = Depends(require_permission("users.manage"))) -> dict[str, Any]:
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute(
            """
            SELECT u.id, u.full_name, u.email, u.username, u.is_active, u.created_at,
                   u.role_id, r.name AS role_name
            FROM users u JOIN roles r ON r.id = u.role_id
            ORDER BY u.created_at DESC, u.id DESC
            """
        )
        return {"users": cursor.fetchall()}
    finally:
        cursor.close()
        conn.close()


@router.put("/api/admin/users/{user_id}/role")
def asignar_rol_a_usuario(
    user_id: int,
    assignment: UserRoleAssignmentRequest,
    request: Request,
    current_user: dict[str, Any] = Depends(require_permission("users.manage")),
) -> dict[str, str]:
    if user_id == current_user["id"]:
        raise HTTPException(status_code=422, detail="No puedes cambiar tu propio rol.")
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        _ensure_audit_log_table(cursor)
        cursor.execute("SELECT id, name FROM roles WHERE id = %s", (assignment.role_id,))
        new_role = cursor.fetchone()
        if not new_role:
            raise HTTPException(status_code=404, detail="No se encontró el rol.")
        cursor.execute(
            """
            SELECT u.id, u.full_name, u.email, u.role_id, r.name AS role_name
            FROM users u JOIN roles r ON r.id = u.role_id
            WHERE u.id = %s
            """,
            (user_id,),
        )
        target_user = cursor.fetchone()
        if not target_user:
            raise HTTPException(status_code=404, detail="No se encontró el usuario.")
        cursor.execute("UPDATE users SET role_id = %s WHERE id = %s", (assignment.role_id, user_id))
        _write_audit_log(
            cursor,
            request,
            current_user,
            "user.role.update",
            "user",
            user_id,
            old_values={
                "role_id": target_user["role_id"],
                "role_name": target_user["role_name"],
            },
            new_values={
                "role_id": new_role["id"],
                "role_name": new_role["name"],
                "full_name": target_user["full_name"],
                "email": target_user["email"],
            },
        )
        conn.commit()
        return {"message": "Rol de usuario actualizado."}
    except Exception:
        conn.rollback()
        raise
    finally:
        cursor.close()
        conn.close()


@router.get("/api/admin/users/{user_id}/permissions")
def obtener_permisos_usuario(
    user_id: int,
    _user: dict[str, Any] = Depends(require_permission("users.manage")),
) -> dict[str, Any]:
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        _ensure_user_permission_schema(cursor)
        conn.commit()
        cursor.execute("SELECT id, role_id FROM users WHERE id = %s", (user_id,))
        target_user = cursor.fetchone()
        if not target_user:
            raise HTTPException(status_code=404, detail="No se encontró el usuario.")
        return {
            "permission_names": _get_effective_user_permissions(
                cursor, target_user["id"], target_user["role_id"]
            )
        }
    finally:
        cursor.close()
        conn.close()


@router.put("/api/admin/users/{user_id}/permissions")
def actualizar_permisos_usuario(
    user_id: int,
    assignment: PermissionAssignmentRequest,
    request: Request,
    current_user: dict[str, Any] = Depends(require_permission("users.manage")),
) -> dict[str, Any]:
    permission_names = sorted(set(assignment.permission_names))
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        _ensure_user_permission_schema(cursor)
        _ensure_audit_log_table(cursor)
        cursor.execute(
            """
            SELECT u.id, u.role_id, u.full_name, u.email, r.name AS role_name
            FROM users u JOIN roles r ON r.id = u.role_id
            WHERE u.id = %s
            """,
            (user_id,),
        )
        target_user = cursor.fetchone()
        if not target_user:
            raise HTTPException(status_code=404, detail="No se encontró el usuario.")

        cursor.execute("SELECT name FROM permissions")
        known_permissions = {row["name"] for row in cursor.fetchall()}
        if set(permission_names) - known_permissions:
            raise HTTPException(status_code=422, detail="La lista contiene permisos no reconocidos.")

        old_permission_names = _get_effective_user_permissions(
            cursor, target_user["id"], target_user["role_id"]
        )
        if user_id == current_user["id"]:
            protected_permissions = {"users.manage"} & set(old_permission_names)
            protected_permissions.update(
                {"roles.manage", "permissions.manage"} & set(old_permission_names)
            )
            if not protected_permissions.issubset(permission_names):
                raise HTTPException(
                    status_code=422,
                    detail="No puedes quitarte permisos necesarios para mantener el acceso administrativo.",
                )

        cursor.execute(
            """
            SELECT p.id, p.name, rp.permission_id IS NOT NULL AS inherited
            FROM permissions p
            LEFT JOIN role_permissions rp
                ON rp.permission_id = p.id AND rp.role_id = %s
            """,
            (target_user["role_id"],),
        )
        permission_rows = cursor.fetchall()
        permission_ids = {row["name"]: row["id"] for row in permission_rows}
        inherited_permissions = {row["name"] for row in permission_rows if row["inherited"]}

        cursor.execute("DELETE FROM user_permissions WHERE user_id = %s", (user_id,))
        overrides = [
            (user_id, permission_ids[name], name in permission_names)
            for name in permission_ids
            if (name in permission_names) != (name in inherited_permissions)
        ]
        if overrides:
            cursor.executemany(
                """
                INSERT INTO user_permissions (user_id, permission_id, is_granted)
                VALUES (%s, %s, %s)
                """,
                overrides,
            )
        _write_audit_log(
            cursor,
            request,
            current_user,
            "user.permissions.update",
            "user",
            user_id,
            old_values={"permission_names": old_permission_names},
            new_values={
                "permission_names": permission_names,
                "full_name": target_user["full_name"],
                "email": target_user["email"],
                "role_name": target_user["role_name"],
            },
        )
        conn.commit()
        return {"user_id": user_id, "permission_names": permission_names}
    except Exception:
        conn.rollback()
        raise
    finally:
        cursor.close()
        conn.close()


@router.get("/api/admin/audit-logs")
def listar_registros_auditoria(
    limit: int = 50,
    offset: int = 0,
    _user: dict[str, Any] = Depends(require_permission("audit.view")),
) -> dict[str, Any]:
    if limit < 1 or limit > 100 or offset < 0:
        raise HTTPException(status_code=422, detail="La paginación solicitada no es válida.")

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        _ensure_audit_log_table(cursor)
        cursor.execute(
            """
            SELECT id, actor_user_id, actor_name, actor_email, action, entity_type,
                   entity_id, old_values, new_values, ip_address, user_agent, created_at
            FROM audit_logs
            ORDER BY created_at DESC, id DESC
            LIMIT %s OFFSET %s
            """,
            (limit + 1, offset),
        )
        logs = cursor.fetchall()
        has_more = len(logs) > limit
        return {"logs": logs[:limit], "has_more": has_more}
    finally:
        cursor.close()
        conn.close()
