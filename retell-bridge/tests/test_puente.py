"""Pruebas del puente. Ejecutar:  pip install pytest  y luego  pytest -q"""
import json
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient
from retell import Retell
from retell.lib.webhook_auth import symmetric

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import catalogo  # noqa: E402
import main  # noqa: E402

CLAVE = "key_de_prueba"


def _fila(i, titulo, categoria, precio, original, descuento, calificacion, resenas):
    return {
        "id": i, "product_title": titulo, "product_category": categoria, "discounted_price": precio,
        "original_price": original, "discount_percentage": descuento, "product_rating": calificacion,
        "total_reviews": resenas, "purchased_last_month": "1K+ bought in past month",
        "buy_box_availability": "Add to cart", "delivery_date": "Mon, Nov 3",
    }


FILAS = [
    _fila(1, "Apple AirPods Pro 2 Wireless Earbuds, Active Noise Cancellation, USB-C", "Phones", "162.24", "249.0", "35.0", "4.6", "35882"),
    _fila(2, "Sony WH-1000XM5 Wireless Headphones, Noise Canceling", "Headphones", "298.0", "399.99", "25.5", "4.5", "9800"),
    _fila(3, "Anker USB C Charger 65W, 3 Port Fast Charger", "Chargers & Cables", "35.99", "49.99", "28.0", "4.7", "15000"),
    _fila(4, "Cheap Wired Earphones with Mic", "Headphones", "7.5", "9.0", "16.0", "3.9", "120"),
    _fila(5, "Gaming Laptop 16 inch RTX Notebook", "Laptops", "1299.0", "1499.0", "13.0", "4.4", "800"),
    _fila(6, "Acer Nitro V Gaming Laptop, 15.6 inch, RTX 4050", "Laptops", "799.0", "899.0", "11.0", "4.2", "627"),
    _fila(7, "ASUS ROG Strix G16 Gaming Laptop, 240Hz", "Laptops", "1899.0", "1999.0", "5.0", "4.1", "544"),
    _fila(8, "Logitech G203 Wired Gaming Mouse for PC Mac Laptop", "Gaming", "24.5", "35.0", "30.0", "4.6", "18261"),
]


class RetellFalso:
    def __init__(self):
        self._real = Retell(api_key=CLAVE)
        self.call = SimpleNamespace(create_web_call=lambda **kw: SimpleNamespace(access_token="token_falso", call_id="call_1"))

    def verify(self, cuerpo, clave, firma):
        return self._real.verify(cuerpo, clave, firma)


@pytest.fixture(autouse=True)
def entorno(monkeypatch):
    monkeypatch.setattr(catalogo, "_descargar", lambda: [i for i in (catalogo._normalizar(f) for f in FILAS) if i])
    catalogo._estado.update({"items": [], "indice": {}, "cargado": 0.0, "actualizando": False})
    monkeypatch.setattr(main, "RETELL_API_KEY", CLAVE)
    monkeypatch.setattr(main, "SKIP_SIGNATURE", False)
    monkeypatch.setattr(main, "ACCESS_CODE", "codigo-secreto")
    monkeypatch.setattr(main, "_retell", RetellFalso())
    main._intentos.clear()
    main._llamadas.clear()
    return TestClient(main.app)


def _firmado(cliente, ruta, args):
    cuerpo = json.dumps({"name": "x", "call": {}, "args": args}, separators=(",", ":"), ensure_ascii=False)
    firma = symmetric["sign"](cuerpo, CLAVE)
    return cliente.post(ruta, content=cuerpo.encode(), headers={"x-retell-signature": firma, "content-type": "application/json"})


def test_busqueda_en_espanol_traduce(entorno):
    r = _firmado(entorno, "/retell/buscar-productos", {"consulta": "audífonos inalámbricos"}).json()
    nombres = [x["nombre"] for x in r["resultados"]]
    assert r["coincidencia"] == "exacta"
    assert any("AirPods" in n for n in nombres) and any("Sony" in n for n in nombres)
    assert all("Charger" not in n for n in nombres)


def test_filtro_de_precio_y_orden(entorno):
    r = _firmado(entorno, "/retell/buscar-productos", {"consulta": "headphones earphones", "precio_max": 50, "orden": "precio_menor"}).json()
    assert [x["id"] for x in r["resultados"]] == [4]


def test_sin_resultados_da_mensaje(entorno):
    r = _firmado(entorno, "/retell/buscar-productos", {"consulta": "lavadora", "precio_max": 5}).json()
    assert r["total_encontrados"] == 0 and "mensaje" in r


def test_respuesta_corta_y_sin_titulo_largo(entorno):
    r = _firmado(entorno, "/retell/buscar-productos", {"consulta": "airpods"}).json()
    assert r["resultados"][0]["nombre"] == "Apple AirPods Pro 2 Wireless Earbuds"
    assert set(r["resultados"][0]) == {"id", "nombre", "precio_usd", "descuento_pct", "calificacion", "resenas"}


def test_detalle_y_no_encontrado(entorno):
    ok = _firmado(entorno, "/retell/detalle-producto", {"id": 3}).json()
    assert ok["precio_original_usd"] == 49.99 and "Anker" in ok["caracteristicas"]
    assert "error" in _firmado(entorno, "/retell/detalle-producto", {"id": 999}).json()


def test_mejores_ofertas_respeta_minimos(entorno):
    r = _firmado(entorno, "/retell/mejores-ofertas", {}).json()
    assert [x["id"] for x in r["resultados"]][0] == 1  # 35 % de descuento, el mayor con buenas reseñas


def test_firma_ausente_o_falsa_se_rechaza(entorno):
    assert entorno.post("/retell/buscar-productos", json={"args": {"consulta": "x"}}).status_code == 401
    r = entorno.post("/retell/buscar-productos", json={"args": {}}, headers={"x-retell-signature": "v=1,d=" + "0" * 64})
    assert r.status_code == 401


def test_catalogo_caido_devuelve_error_legible(entorno, monkeypatch):
    def falla():
        raise catalogo.CatalogoNoDisponible("sin conexión")
    monkeypatch.setattr(catalogo, "_descargar", falla)
    r = _firmado(entorno, "/retell/buscar-productos", {"consulta": "laptop"})
    assert r.status_code == 200 and "error" in r.json()
    assert entorno.get("/health").json()["catalogo"] == "no_disponible"


def test_crear_llamada_codigo(entorno):
    assert entorno.post("/api/crear-llamada", json={"codigo": "mal"}).status_code == 401
    ok = entorno.post("/api/crear-llamada", json={"codigo": "codigo-secreto"})
    assert ok.status_code == 200 and ok.json() == {"access_token": "token_falso", "call_id": "call_1"}


def test_crear_llamada_limita_intentos(entorno):
    for _ in range(main.MAX_ATTEMPTS_PER_10_MIN):
        entorno.post("/api/crear-llamada", json={"codigo": "mal"})
    assert entorno.post("/api/crear-llamada", json={"codigo": "codigo-secreto"}).status_code == 429


def test_tope_global_de_llamadas(entorno, monkeypatch):
    monkeypatch.setattr(main, "MAX_CALLS_PER_HOUR", 2)
    codigos = [entorno.post("/api/crear-llamada", json={"codigo": "codigo-secreto"}).status_code for _ in range(3)]
    assert codigos == [200, 200, 429]


def test_webhook_firmado(entorno):
    cuerpo = json.dumps({"event": "call_ended", "call": {"call_id": "c1"}}, separators=(",", ":"))
    firma = symmetric["sign"](cuerpo, CLAVE)
    r = entorno.post("/retell/webhook", content=cuerpo.encode(), headers={"x-retell-signature": firma})
    assert r.status_code == 200 and r.json() == {"ok": True}
    assert entorno.post("/retell/webhook", content=cuerpo.encode()).status_code == 401


def test_pagina_y_cabecera_de_microfono(entorno):
    r = entorno.get("/asistente")
    assert r.status_code == 200 and "Vortex" in r.text
    assert r.headers["permissions-policy"] == "microphone=(self)"
    assert entorno.get("/static/retell-client.js").status_code == 200


def test_accesorios_no_tapan_a_los_productos(entorno):
    r = _firmado(entorno, "/retell/buscar-productos", {"consulta": "gaming laptop", "orden": "mas_resenas"}).json()
    ids = [x["id"] for x in r["resultados"]]
    assert 8 not in ids and set(ids) == {5, 6, 7}  # el mouse solo menciona "laptop" en la descripción


def test_nombre_corto_sin_cortes_feos():
    assert catalogo.nombre_corto("DJI Mic 2 (2 TX + 1 RX + Charging Case), Wireless Lavalier Microphone") == "DJI Mic 2"
    assert catalogo.nombre_corto("UGREEN Vertical Laptop Stand Holder for Desk Compatible with Macbook") == "UGREEN Vertical Laptop Stand Holder for Desk"


def test_ofertas_por_tipo_de_producto(entorno):
    r = _firmado(entorno, "/retell/mejores-ofertas", {"consulta": "audífonos"}).json()
    assert r["resultados"] and all(x["id"] in {1, 2, 4} for x in r["resultados"])
    assert r["resultados"][0]["id"] == 1  # el de mayor descuento con reseñas suficientes
