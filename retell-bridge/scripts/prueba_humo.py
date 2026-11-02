"""Prueba sin voz de la cadena de acciones del puente Retell."""
from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any
from urllib.parse import quote

import httpx
from dotenv import dotenv_values

BRIDGE_ROOT = Path(__file__).resolve().parents[1]


class SmokeError(Exception):
    """Error de una respuesta HTTP sin incluir sus datos en la salida."""


def _json_response(response: httpx.Response) -> Any:
    if not response.is_success:
        raise SmokeError(f"HTTP {response.status_code}")
    try:
        return response.json()
    except ValueError as exc:
        raise SmokeError("respuesta JSON no válida") from exc


def _acciones(
    client: httpx.Client,
    bridge: str,
    call_id: str,
    desde: int,
) -> dict[str, Any]:
    path_id = quote(call_id, safe="")
    data = _json_response(
        client.get(f"{bridge}/api/acciones/{path_id}", params={"desde": desde})
    )
    if not isinstance(data, dict):
        raise SmokeError("formato de acciones no válido")
    return data


def _resultados_producto(client: httpx.Client, backend: str) -> set[int]:
    data = _json_response(client.get(f"{backend}/api/productos"))
    productos = data.get("productos") if isinstance(data, dict) else None
    if not isinstance(productos, list):
        raise SmokeError("el backend no devolvió una lista de productos")
    return {
        int(producto["id"])
        for producto in productos
        if isinstance(producto, dict)
        and str(producto.get("id", "")).isdigit()
        and int(producto["id"]) > 0
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--puente", default="http://localhost:8001")
    parser.add_argument("--publica", required=True, help="URL pública del túnel del puente.")
    args = parser.parse_args()

    bridge = args.puente.rstrip("/")
    public = args.publica.rstrip("/")
    config = dotenv_values(BRIDGE_ROOT / ".env")
    access_code = config.get("ACCESS_CODE")
    backend = str(config.get("BACKEND_URL") or "http://localhost:8000").rstrip("/")
    skip_signature = str(config.get("DEV_SKIP_SIGNATURE") or "false").lower() == "true"
    results: list[tuple[str, str, str]] = []

    def record(step: str, status: str, detail: str) -> None:
        results.append((step, status, detail))

    call_id: str | None = None
    cursor = 0
    with httpx.Client(timeout=30, follow_redirects=True) as client:
        health_ok = True
        for label, url in (("túnel", f"{public}/health"), ("puente", f"{bridge}/health")):
            try:
                data = _json_response(client.get(url))
                if not isinstance(data, dict) or data.get("status") != "ok" or data.get("catalogo") != "listo":
                    raise SmokeError("status/catalogo no están listos")
            except (httpx.HTTPError, SmokeError) as exc:
                health_ok = False
                record("a. health", "FALLA", f"{label}: {type(exc).__name__ if isinstance(exc, httpx.HTTPError) else exc}")
            else:
                record("a. health", "PASA", f"{label}: status ok, catálogo listo")

        if not access_code:
            record("b. crear llamada", "FALLA", "ACCESS_CODE falta en retell-bridge/.env")
        else:
            try:
                response = client.post(
                    f"{bridge}/api/crear-llamada",
                    json={"codigo": access_code},
                )
                data = _json_response(response)
                required = ("access_token", "call_id", "transport", "ice_servers")
                if not isinstance(data, dict) or any(key not in data for key in required):
                    raise SmokeError("faltan campos de llamada")
                if (
                    not data["access_token"]
                    or not data["call_id"]
                    or not data["transport"]
                    or not isinstance(data["ice_servers"], list)
                ):
                    raise SmokeError("campos de llamada vacíos o inválidos")
                call_id = str(data["call_id"])
                record("b. crear llamada", "PASA", f"campos completos; call_id={call_id[:6]}…")
            except (httpx.HTTPError, SmokeError) as exc:
                detail = f"HTTP/red: {type(exc).__name__}" if isinstance(exc, httpx.HTTPError) else str(exc)
                record("b. crear llamada", "FALLA", detail)

        backend_ids: set[int] | None = None
        search_action: dict[str, Any] | None = None
        if not call_id:
            record("c. simular búsqueda", "BLOQUEADO", "requiere una llamada creada")
            record("d. verificar IDs", "BLOQUEADO", "requiere la acción de búsqueda")
            record("e. detalle y navegación", "BLOQUEADO", "requiere la acción de búsqueda")
        elif not skip_signature:
            record(
                "c. simular búsqueda",
                "FALLA",
                "DEV_SKIP_SIGNATURE=false; no se envió. En .env local: true (APP_ENV no producción), reinicia puente; restaura false al acabar",
            )
            record("d. verificar IDs", "BLOQUEADO", "requiere ejecutar la búsqueda simulada")
            record("e. detalle y navegación", "BLOQUEADO", "requiere ejecutar la búsqueda simulada")
        else:
            try:
                search = _json_response(
                    client.post(
                        f"{bridge}/retell/buscar-productos",
                        json={
                            "name": "buscar_productos",
                            "call": {"call_id": call_id},
                            "args": {"consulta": "laptop"},
                        },
                    )
                )
                baseline = _acciones(client, bridge, call_id, 0)
                actions = baseline.get("acciones")
                search_action = next(
                    (
                        item
                        for item in actions
                        if isinstance(item, dict)
                        and item.get("tipo") in {"mostrar_productos", "catalogo"}
                    ),
                    None,
                ) if isinstance(actions, list) else None
                ids = search_action.get("ids") if search_action else None
                if (
                    not isinstance(search, dict)
                    or "resultados" not in search
                    or not isinstance(ids, list)
                    or not ids
                ):
                    raise SmokeError("búsqueda sin resultados o sin acción de catálogo")
                cursor = int(baseline.get("ultimo", 0))
                record("c. simular búsqueda", "PASA", "búsqueda de laptop aceptada")
            except (httpx.HTTPError, SmokeError, TypeError, ValueError) as exc:
                detail = f"HTTP/red: {type(exc).__name__}" if isinstance(exc, httpx.HTTPError) else str(exc)
                record("c. simular búsqueda", "FALLA", detail)
                record("d. verificar IDs", "BLOQUEADO", "no se obtuvo una acción de búsqueda válida")
                record("e. detalle y navegación", "BLOQUEADO", "no se obtuvo una acción de búsqueda válida")
            else:
                try:
                    backend_ids = _resultados_producto(client, backend)
                    ids = [int(product_id) for product_id in search_action["ids"]]
                    missing_ids = [product_id for product_id in ids if product_id not in backend_ids]
                    if missing_ids:
                        raise SmokeError(f"{len(missing_ids)} id(s) de la acción no existen en el catálogo")
                    record("d. verificar IDs", "PASA", f"{len(ids)} id(s) existen en el backend")
                except (httpx.HTTPError, SmokeError, TypeError, ValueError) as exc:
                    detail = f"HTTP/red: {type(exc).__name__}" if isinstance(exc, httpx.HTTPError) else str(exc)
                    record("d. verificar IDs", "FALLA", detail)

                if backend_ids is None or not search_action or not search_action.get("ids"):
                    record("e. detalle y navegación", "BLOQUEADO", "no hay un id válido para el detalle")
                else:
                    product_id = int(search_action["ids"][0])
                    try:
                        detail_result = _json_response(
                            client.post(
                                f"{bridge}/retell/detalle-producto",
                                json={
                                    "name": "detalle_producto",
                                    "call": {"call_id": call_id},
                                    "args": {"id": product_id},
                                },
                            )
                        )
                        detail_actions = _acciones(client, bridge, call_id, cursor)
                        detail_action = next(
                            (
                                item
                                for item in detail_actions.get("acciones", [])
                                if isinstance(item, dict)
                                and item.get("tipo") in {"abrir_producto", "producto"}
                            ),
                            None,
                        )
                        if not isinstance(detail_result, dict) or not detail_action:
                            raise SmokeError("no se encoló la acción de abrir producto")
                        cursor = int(detail_actions.get("ultimo", cursor))

                        nav_result = _json_response(
                            client.post(
                                f"{bridge}/retell/navegar",
                                json={
                                    "name": "navegar",
                                    "call": {"call_id": call_id},
                                    "args": {"destino": "perfil"},
                                },
                            )
                        )
                        nav_actions = _acciones(client, bridge, call_id, cursor)
                        nav_action = next(
                            (
                                item
                                for item in nav_actions.get("acciones", [])
                                if isinstance(item, dict)
                                and item.get("tipo") in {"ir_a", "navegar"}
                                and item.get("destino") == "perfil"
                            ),
                            None,
                        )
                        if (
                            not isinstance(nav_result, dict)
                            or nav_result.get("destino") != "perfil"
                            or not nav_action
                        ):
                            raise SmokeError("no se encoló la acción de navegar a perfil")
                        cursor = int(nav_actions.get("ultimo", cursor))
                        record("e. detalle y navegación", "PASA", "abrir producto y navegar a perfil")
                    except (httpx.HTTPError, SmokeError, TypeError, ValueError) as exc:
                        detail = f"HTTP/red: {type(exc).__name__}" if isinstance(exc, httpx.HTTPError) else str(exc)
                        record("e. detalle y navegación", "FALLA", detail)

        if call_id:
            try:
                remaining = _acciones(client, bridge, call_id, cursor)
                unknown_status = client.get(
                    f"{bridge}/api/acciones/inventado-por-prueba",
                    params={"desde": 0},
                ).status_code
                if remaining.get("acciones") != []:
                    raise SmokeError("el cursor no devolvió una lista vacía")
                if unknown_status != 404:
                    raise SmokeError(
                        f"call_id inventado devolvió HTTP {unknown_status}, se esperaba 404; "
                        "reinicia el puente para cargar el código actualizado"
                    )
                record("f. cursor y call_id inválido", "PASA", "cursor vacío; call_id inventado devuelve 404")
            except (httpx.HTTPError, SmokeError) as exc:
                detail = f"HTTP/red: {type(exc).__name__}" if isinstance(exc, httpx.HTTPError) else str(exc)
                record("f. cursor y call_id inválido", "FALLA", detail)
        else:
            record("f. cursor y call_id inválido", "BLOQUEADO", "requiere una llamada creada")

    print(f"\nPuente probado: {bridge}")
    print(f"Túnel probado: {public}")
    print(f"Estado firma simulada: {'habilitada localmente' if skip_signature else 'deshabilitada; no se modificó'}")
    print(f"{'Paso':34} {'Resultado':12} Detalle")
    print("-" * 100)
    for step, status, detail in results:
        print(f"{step:34} {status:12} {detail}")
    return 0 if results and all(status == "PASA" for _, status, _ in results) and health_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
