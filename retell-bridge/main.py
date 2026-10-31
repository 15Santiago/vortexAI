"""Puente entre el agente de voz de Retell y vortexAI.

No modifica el backend existente: lee su catálogo público y expone
  - las funciones que Retell llama durante la conversación (/retell/...),
  - la creación de la llamada web (/api/crear-llamada),
  - la página de voz (/asistente),
  - un webhook opcional de fin de llamada (/retell/webhook).
"""
from __future__ import annotations

import hmac
import json
import logging
import os
import threading
import time
from collections import defaultdict, deque
from pathlib import Path
from typing import Any, Callable

import httpx
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from retell import Retell
from starlette.concurrency import run_in_threadpool

import catalogo

load_dotenv()
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
log = logging.getLogger("puente")

BASE = Path(__file__).resolve().parent
PRODUCTION = os.getenv("APP_ENV", "development").lower() == "production"
RETELL_API_KEY = os.getenv("RETELL_API_KEY", "")
RETELL_AGENT_ID = os.getenv("RETELL_AGENT_ID", "")
ACCESS_CODE = os.getenv("ACCESS_CODE", "")
SKIP_SIGNATURE = os.getenv("DEV_SKIP_SIGNATURE", "false").lower() == "true" and not PRODUCTION
MAX_CALLS_PER_HOUR = int(os.getenv("MAX_CALLS_PER_HOUR", "30"))
MAX_ATTEMPTS_PER_10_MIN = 8

if PRODUCTION and not (RETELL_API_KEY and RETELL_AGENT_ID and ACCESS_CODE):
    raise RuntimeError("En producción deben estar definidas RETELL_API_KEY, RETELL_AGENT_ID y ACCESS_CODE.")

_retell = Retell(api_key=RETELL_API_KEY or "sin-clave")

app = FastAPI(title="vortexAI · puente de Retell", docs_url=None if PRODUCTION else "/docs", redoc_url=None)
app.mount("/static", StaticFiles(directory=BASE / "static"), name="static")

_origenes = [o.strip() for o in os.getenv("CORS_ORIGINS", "").split(",") if o.strip()]
if _origenes:
    app.add_middleware(CORSMiddleware, allow_origins=_origenes, allow_methods=["GET", "POST"], allow_headers=["Content-Type"])


@app.middleware("http")
async def cabeceras_de_seguridad(request: Request, call_next):
    respuesta = await call_next(request)
    respuesta.headers["X-Content-Type-Options"] = "nosniff"
    respuesta.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    # El backend principal bloquea el micrófono; esta página lo necesita.
    respuesta.headers["Permissions-Policy"] = "microphone=(self)"
    return respuesta


# ---------------------------------------------------------------- páginas
@app.get("/", include_in_schema=False)
def inicio() -> RedirectResponse:
    return RedirectResponse("/asistente")


@app.get("/asistente", include_in_schema=False)
def pagina_asistente() -> FileResponse:
    return FileResponse(BASE / "static" / "asistente.html", headers={"Cache-Control": "no-cache"})


@app.get("/health")
def health() -> dict[str, Any]:
    """Despierta el servicio y el catálogo. Siempre responde 200 para no reiniciar la app por error."""
    try:
        catalogo.obtener()
        estado = "listo"
    except catalogo.CatalogoNoDisponible as exc:
        log.warning("Catálogo no disponible en /health: %s", exc)
        estado = "no_disponible"
    return {"status": "ok", "catalogo": estado, **catalogo.estado()}


# ---------------------------------------------------------------- funciones de Retell
def _verificar_firma(crudo: bytes, firma: str | None) -> None:
    if SKIP_SIGNATURE:
        return
    if not RETELL_API_KEY or not firma or not _retell.verify(crudo.decode("utf-8"), RETELL_API_KEY, firma):
        raise HTTPException(status_code=401, detail="Firma inválida.")


async def _leer_argumentos(request: Request) -> dict[str, Any]:
    crudo = await request.body()
    _verificar_firma(crudo, request.headers.get("x-retell-signature"))
    try:
        cuerpo = json.loads(crudo or b"{}")
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Cuerpo no válido.") from exc
    if isinstance(cuerpo, dict) and isinstance(cuerpo.get("args"), dict):
        return cuerpo["args"]  # formato normal de Retell: {name, call, args}
    return cuerpo if isinstance(cuerpo, dict) else {}


async def _ejecutar(funcion: Callable[..., dict[str, Any]], argumentos: dict[str, Any]) -> dict[str, Any]:
    try:
        return await run_in_threadpool(funcion, **argumentos)
    except catalogo.CatalogoNoDisponible as exc:
        log.warning("Catálogo no disponible: %s", exc)
        return {"error": "El catálogo no está disponible por ahora. Intenta de nuevo en un momento."}
    except TypeError:
        return {"error": "Los datos de la consulta no son válidos."}
    except Exception:  # noqa: BLE001 - el agente siempre debe recibir una respuesta
        log.exception("Error en la función %s", getattr(funcion, "__name__", "?"))
        return {"error": "Ocurrió un problema al consultar el catálogo."}


@app.post("/retell/buscar-productos")
async def retell_buscar_productos(request: Request) -> dict[str, Any]:
    return await _ejecutar(catalogo.buscar, await _leer_argumentos(request))


@app.post("/retell/detalle-producto")
async def retell_detalle_producto(request: Request) -> dict[str, Any]:
    return await _ejecutar(catalogo.detalle, await _leer_argumentos(request))


@app.post("/retell/mejores-ofertas")
async def retell_mejores_ofertas(request: Request) -> dict[str, Any]:
    return await _ejecutar(catalogo.mejores_ofertas, await _leer_argumentos(request))


# ---------------------------------------------------------------- llamada web
_candado = threading.Lock()
_intentos: dict[str, deque[float]] = defaultdict(deque)
_llamadas: deque[float] = deque()


def _ip_cliente(request: Request) -> str:
    reenviado = request.headers.get("x-forwarded-for", "")
    if reenviado:
        # La última IP la añade el proxy de Azure; las anteriores las puede falsear el cliente.
        ultima = reenviado.split(",")[-1].strip()
        return ultima.rsplit(":", 1)[0] if ultima.count(":") == 1 else ultima  # quita el puerto de IPv4
    return request.client.host if request.client else "desconocida"


def _permitir_intento(ip: str) -> bool:
    ahora = time.time()
    with _candado:
        if len(_intentos) > 10_000:
            _intentos.clear()
        cola = _intentos[ip]
        while cola and ahora - cola[0] > 600:
            cola.popleft()
        if len(cola) >= MAX_ATTEMPTS_PER_10_MIN:
            return False
        cola.append(ahora)
        return True


def _hay_cupo_de_llamadas() -> bool:
    ahora = time.time()
    with _candado:
        while _llamadas and ahora - _llamadas[0] > 3600:
            _llamadas.popleft()
        if len(_llamadas) >= MAX_CALLS_PER_HOUR:
            return False
        _llamadas.append(ahora)
        return True


class SolicitudLlamada(BaseModel):
    codigo: str = ""


@app.post("/api/crear-llamada")
def crear_llamada(datos: SolicitudLlamada, request: Request) -> dict[str, str]:
    if not _permitir_intento(_ip_cliente(request)):
        raise HTTPException(status_code=429, detail="Demasiados intentos. Espera unos minutos.")
    if not ACCESS_CODE or not hmac.compare_digest(datos.codigo.encode(), ACCESS_CODE.encode()):
        raise HTTPException(status_code=401, detail="Código de acceso incorrecto.")
    if not _hay_cupo_de_llamadas():
        raise HTTPException(status_code=429, detail="Se alcanzó el límite de llamadas por hora. Intenta más tarde.")
    try:
        llamada = _retell.call.create_web_call(agent_id=RETELL_AGENT_ID, metadata={"origen": "vortexai-asistente"})
    except Exception:  # noqa: BLE001
        log.exception("Retell no pudo crear la llamada web")
        raise HTTPException(status_code=502, detail="No se pudo iniciar la llamada. Intenta de nuevo.") from None
    return {"access_token": llamada.access_token, "call_id": llamada.call_id}


# ---------------------------------------------------------------- webhook de fin de llamada (opcional)
def _avisar_telegram(texto: str) -> None:
    token, chat = os.getenv("TELEGRAM_BOT_TOKEN"), os.getenv("TELEGRAM_CHAT_ID")
    if not token or not chat:
        return
    try:
        httpx.post(f"https://api.telegram.org/bot{token}/sendMessage", json={"chat_id": chat, "text": texto[:3500]}, timeout=10)
    except httpx.HTTPError:
        log.warning("No se pudo enviar el aviso a Telegram.")  # sin detalle: la URL contiene el token


@app.post("/retell/webhook")
async def retell_webhook(request: Request) -> dict[str, bool]:
    crudo = await request.body()
    _verificar_firma(crudo, request.headers.get("x-retell-signature"))
    try:
        datos = json.loads(crudo or b"{}")
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Cuerpo no válido.") from exc
    evento, llamada = datos.get("event"), datos.get("call") or {}
    log.info("Webhook de Retell: %s (llamada %s)", evento, llamada.get("call_id"))
    if evento == "call_analyzed":
        inicio, fin = llamada.get("start_timestamp"), llamada.get("end_timestamp")
        segundos = round((fin - inicio) / 1000) if isinstance(inicio, (int, float)) and isinstance(fin, (int, float)) else "?"
        resumen = (llamada.get("call_analysis") or {}).get("call_summary") or "Sin resumen."
        await run_in_threadpool(_avisar_telegram, f"Llamada con Vortex terminada ({segundos} s)\n{resumen}")
    return {"ok": True}
