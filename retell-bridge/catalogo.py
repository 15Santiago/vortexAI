"""Catálogo en memoria para el asistente de voz.

Descarga la lista pública GET {BACKEND_URL}/api/productos (sin tocar la base de datos),
la guarda en memoria y la refresca cada CATALOG_TTL_SECONDS. Las búsquedas se hacen aquí.
"""
from __future__ import annotations

import logging
import math
import os
import re
import threading
import time
import unicodedata
from typing import Any

import httpx

logger = logging.getLogger("puente.catalogo")

MAX_RESULTADOS = 5

CATEGORIAS = [
    "Other Electronics", "Laptops", "Phones", "Cameras", "Power & Batteries", "TV & Display",
    "Chargers & Cables", "Storage", "Speakers", "Networking", "Headphones",
    "Printers & Scanners", "Gaming", "Smart Home", "Wearables",
]
ALIAS_CATEGORIA = {
    "portatil": "Laptops", "portatiles": "Laptops", "computadores": "Laptops",
    "telefono": "Phones", "telefonos": "Phones", "celulares": "Phones",
    "audifonos": "Headphones", "camaras": "Cameras", "televisores": "TV & Display",
    "pantallas": "TV & Display", "cargadores y cables": "Chargers & Cables",
    "energia y baterias": "Power & Batteries", "almacenamiento": "Storage",
    "parlantes": "Speakers", "redes": "Networking", "impresoras y escaneres": "Printers & Scanners",
    "videojuegos": "Gaming", "hogar inteligente": "Smart Home", "otros electronicos": "Other Electronics",
}

# Los títulos del catálogo están en inglés: si el agente manda una palabra en español, se amplía.
SINONIMOS = {
    "audifono": ["headphone", "earbud", "earphone", "headset"],
    "auricular": ["headphone", "earbud", "earphone", "headset"],
    "cargador": ["charger", "charging"],
    "computador": ["laptop", "notebook", "computer"],
    "computadora": ["laptop", "notebook", "computer"],
    "portatil": ["laptop", "notebook"],
    "telefono": ["phone", "smartphone", "iphone", "galaxy"],
    "celular": ["phone", "smartphone", "iphone", "galaxy"],
    "movil": ["phone", "smartphone"],
    "parlante": ["speaker", "soundbar"],
    "altavoz": ["speaker"],
    "bocina": ["speaker"],
    "camara": ["camera", "webcam"],
    "televisor": ["tv", "television"],
    "television": ["tv", "television"],
    "pantalla": ["monitor", "display", "screen", "tv"],
    "impresora": ["printer"],
    "escaner": ["scanner"],
    "reloj": ["watch", "smartwatch"],
    "pulsera": ["band", "tracker", "fitness"],
    "raton": ["mouse"],
    "teclado": ["keyboard"],
    "bateria": ["battery", "power bank", "powerbank"],
    "pila": ["battery"],
    "disco": ["ssd", "hard drive", "hdd", "drive"],
    "memoria": ["memory", "flash drive", "sd card", "ssd"],
    "almacenamiento": ["storage", "ssd", "hard drive", "flash drive"],
    "microfono": ["microphone", "mic"],
    "inalambrico": ["wireless", "bluetooth"],
    "consola": ["console", "gaming"],
    "juego": ["gaming", "game"],
    "videojuego": ["gaming", "game", "console"],
    "gamer": ["gaming"],
    "red": ["router", "wifi", "mesh", "network"],
}
STOPWORDS = {
    "de", "del", "la", "el", "los", "las", "un", "una", "unos", "unas", "para", "con", "y", "o", "que",
    "quiero", "busco", "necesito", "barato", "baratos", "barata", "economico", "economicos", "bueno",
    "buena", "mejor", "mejores", "the", "an", "for", "and", "with", "of", "in", "to", "me", "mi", "en",
}


class CatalogoNoDisponible(Exception):
    """No se pudo leer el catálogo del backend."""


def _sin_acentos(texto: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFKD", texto) if not unicodedata.combining(c))


def _num(valor: Any) -> float | None:
    try:
        n = float(valor)
    except (TypeError, ValueError):
        return None
    return None if math.isnan(n) else n


def _texto(valor: Any) -> str | None:
    if valor is None:
        return None
    return str(valor).strip() or None


def _bool(valor: Any) -> bool:
    if isinstance(valor, str):
        return valor.strip().lower() in {"true", "1", "si", "sí", "yes"}
    return bool(valor)


_CONECTORES = {"for", "with", "and", "&", "compatible", "by", "to", "in", "of", "+", "-", "|", "w/"}


def nombre_corto(titulo: str, max_palabras: int = 8) -> str:
    """Marca + tipo + modelo: corta en la primera coma, barra o guion largo y limpia el final."""
    primero = re.split(r",| \| | - | – ", titulo, maxsplit=1)[0].strip()
    palabras = primero.split()[:max_palabras]
    nombre = " ".join(palabras)
    if nombre.count("(") > nombre.count(")"):
        nombre = nombre[: nombre.rfind("(")].rstrip()
        palabras = nombre.split()
    while palabras and palabras[-1].lower() in _CONECTORES:
        palabras.pop()
    return " ".join(palabras)


def _normalizar(fila: dict[str, Any]) -> dict[str, Any] | None:
    titulo = _texto(fila.get("product_title"))
    if not titulo or fila.get("id") is None:
        return None
    return {
        "id": int(fila["id"]),
        "titulo": titulo,
        "buscar": _sin_acentos(titulo).lower(),
        "nombre_buscar": _sin_acentos(nombre_corto(titulo)).lower(),
        "categoria": _texto(fila.get("product_category")),
        "precio": _num(fila.get("discounted_price")),
        "original": _num(fila.get("original_price")),
        "descuento": _num(fila.get("discount_percentage")) or 0.0,
        "calificacion": _num(fila.get("product_rating")),
        "resenas": int(_num(fila.get("total_reviews")) or 0),
        "comprados": _texto(fila.get("purchased_last_month")),
        "disponibilidad": _texto(fila.get("buy_box_availability")),
        "entrega": _texto(fila.get("delivery_date")),
    }


# ---------------------------------------------------------------- caché
_estado: dict[str, Any] = {"items": [], "indice": {}, "cargado": 0.0, "actualizando": False}
_candado = threading.Lock()


def _ttl() -> int:
    return int(os.getenv("CATALOG_TTL_SECONDS", "600"))


def _descargar() -> list[dict[str, Any]]:
    base = os.getenv("BACKEND_URL", "http://localhost:8000").rstrip("/")
    url = f"{base}/api/productos"
    try:
        with httpx.Client(timeout=httpx.Timeout(90.0, connect=10.0), follow_redirects=True) as cliente:
            respuesta = cliente.get(url)
            respuesta.raise_for_status()
            filas = respuesta.json().get("productos", [])
    except (httpx.HTTPError, ValueError, AttributeError) as exc:
        raise CatalogoNoDisponible(f"No se pudo leer {url}: {exc}") from exc
    items = [i for i in (_normalizar(f) for f in filas) if i]
    if not items:
        raise CatalogoNoDisponible("El backend devolvió un catálogo vacío.")
    return items


def _publicar(items: list[dict[str, Any]]) -> None:
    _estado["items"] = items
    _estado["indice"] = {p["id"]: p for p in items}
    _estado["cargado"] = time.time()


def _refrescar() -> None:
    try:
        _publicar(_descargar())
        logger.info("Catálogo actualizado: %s productos", len(_estado["items"]))
    except CatalogoNoDisponible as exc:
        logger.warning("No se pudo refrescar el catálogo (se usa la copia anterior): %s", exc)
        _estado["cargado"] = time.time() - _ttl() + 60  # reintenta en ~1 minuto
    finally:
        _estado["actualizando"] = False


def obtener() -> list[dict[str, Any]]:
    if not _estado["items"]:
        with _candado:
            if not _estado["items"]:
                _publicar(_descargar())
                logger.info("Catálogo cargado: %s productos", len(_estado["items"]))
    elif time.time() - _estado["cargado"] > _ttl() and not _estado["actualizando"]:
        _estado["actualizando"] = True
        threading.Thread(target=_refrescar, daemon=True).start()
    return _estado["items"]


def estado() -> dict[str, Any]:
    cargado = _estado["cargado"]
    return {
        "productos": len(_estado["items"]),
        "edad_segundos": round(time.time() - cargado) if cargado else None,
    }


# ---------------------------------------------------------------- búsqueda
def _tokens(consulta: str | None) -> list[str]:
    normal = _sin_acentos(consulta or "").lower()
    return [p for p in re.findall(r"[a-z0-9+]+", normal) if len(p) > 1 and p not in STOPWORDS]


def _patrones(tokens: list[str]) -> list[re.Pattern[str]]:
    grupos = []
    for token in tokens:
        base = token[:-1] if token.endswith("s") and len(token) > 3 else token
        alternativas = [token] + SINONIMOS.get(token, SINONIMOS.get(base, []))
        grupos.append(re.compile(r"\b(?:" + "|".join(re.escape(a) for a in alternativas) + ")"))
    return grupos


def _categoria(valor: Any) -> str | None:
    if not valor:
        return None
    normal = _sin_acentos(str(valor)).lower().strip()
    for nombre in CATEGORIAS:
        if normal == nombre.lower():
            return nombre
    return ALIAS_CATEGORIA.get(normal)


def _redondear(valor: float | None) -> float | None:
    return None if valor is None else round(valor, 2)


def _resumen(p: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": p["id"],
        "nombre": nombre_corto(p["titulo"]),
        "precio_usd": _redondear(p["precio"]),
        "descuento_pct": round(p["descuento"]),
        "calificacion": p["calificacion"],
        "resenas": p["resenas"],
    }


MIN_COINCIDENCIAS_EN_NOMBRE = 3  # si hay al menos 3 productos cuyo NOMBRE coincide, se descartan los accesorios


def _candidatos(items: list[dict[str, Any]], grupos: list[re.Pattern[str]]) -> list[tuple[int, int, dict[str, Any]]]:
    """(palabras halladas en el nombre, palabras halladas en todo el título, producto)."""
    return [
        (
            sum(1 for g in grupos if g.search(p["nombre_buscar"])),
            sum(1 for g in grupos if g.search(p["buscar"])),
            p,
        )
        for p in items
    ]


def _por_niveles(candidatos: list[tuple[int, int, dict[str, Any]]], grupos: list[re.Pattern[str]]) -> tuple[list, str]:
    """Primero productos cuyo nombre coincide; si faltan, todo el título; si no, coincidencia parcial."""
    if not grupos:
        return candidatos, "exacta"
    n = len(grupos)
    en_el_nombre = [c for c in candidatos if c[0] == n]
    if len(en_el_nombre) >= MIN_COINCIDENCIAS_EN_NOMBRE:
        return en_el_nombre, "exacta"
    en_el_titulo = [c for c in candidatos if c[1] == n]
    if en_el_titulo:
        return en_el_titulo, "exacta"
    return [c for c in candidatos if c[1] >= math.ceil(n / 2)], "parcial"


def buscar(
    consulta: str = "",
    precio_max: Any = None,
    calificacion_min: Any = None,
    solo_descuento: Any = False,
    orden: str = "relevancia",
    categoria: Any = None,
    **_ignorados: Any,
) -> dict[str, Any]:
    items = obtener()
    grupos = _patrones(_tokens(consulta))
    tope, minimo, cat = _num(precio_max), _num(calificacion_min), _categoria(categoria)
    solo_descuento = _bool(solo_descuento)

    filtrados = [
        p for p in items
        if (not cat or p["categoria"] == cat)
        and (tope is None or (p["precio"] is not None and p["precio"] <= tope))
        and (minimo is None or (p["calificacion"] or 0) >= minimo)
        and (not solo_descuento or p["descuento"] > 0)
    ]
    seleccion, tipo = _por_niveles(_candidatos(filtrados, grupos), grupos)

    if orden == "precio_menor":
        seleccion.sort(key=lambda c: (c[2]["precio"] is None, c[2]["precio"] or 0, -c[2]["resenas"]))
    elif orden == "calificacion":
        seleccion.sort(key=lambda c: (-(c[2]["calificacion"] or 0) if c[2]["resenas"] >= 20 else 0, -c[2]["resenas"]))
    elif orden == "descuento":
        seleccion.sort(key=lambda c: (-c[2]["descuento"], -c[2]["resenas"]))
    elif orden == "mas_resenas":
        seleccion.sort(key=lambda c: -c[2]["resenas"])
    else:
        seleccion.sort(key=lambda c: (-c[0], -c[1], -c[2]["resenas"]))

    salida: dict[str, Any] = {
        "total_encontrados": len(seleccion),
        "resultados": [_resumen(c[2]) for c in seleccion[:MAX_RESULTADOS]],
    }
    if seleccion:
        salida["coincidencia"] = tipo
    else:
        salida["mensaje"] = "No hay productos con esos criterios."
    return salida


def mejores_ofertas(consulta: str = "", categoria: Any = None, precio_max: Any = None, **_ignorados: Any) -> dict[str, Any]:
    grupos = _patrones(_tokens(consulta))
    cat, tope = _categoria(categoria), _num(precio_max)
    filtrados = [
        p for p in obtener()
        if p["descuento"] > 0 and p["resenas"] >= 50 and (p["calificacion"] or 0) >= 3.5
        and (not cat or p["categoria"] == cat)
        and (tope is None or (p["precio"] is not None and p["precio"] <= tope))
    ]
    seleccion, _ = _por_niveles(_candidatos(filtrados, grupos), grupos)
    seleccion.sort(key=lambda c: (-c[2]["descuento"], -c[2]["resenas"]))
    salida: dict[str, Any] = {
        "total_encontrados": len(seleccion),
        "resultados": [_resumen(c[2]) for c in seleccion[:MAX_RESULTADOS]],
    }
    if not seleccion:
        salida["mensaje"] = "No hay ofertas con esos criterios."
    return salida


def detalle(id: Any = None, **_ignorados: Any) -> dict[str, Any]:  # noqa: A002 - nombre exigido por la función de Retell
    obtener()
    numero = _num(id)
    producto = _estado["indice"].get(int(numero)) if numero is not None else None
    if not producto:
        return {"error": "No encontré ese producto."}
    return {
        **_resumen(producto),
        "categoria": producto["categoria"],
        "precio_original_usd": _redondear(producto["original"]),
        "comprados_ultimo_mes": producto["comprados"],
        "disponibilidad": producto["disponibilidad"],
        "entrega": producto["entrega"],
        "caracteristicas": producto["titulo"][:300],
    }
