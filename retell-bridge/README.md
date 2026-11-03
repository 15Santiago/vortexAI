# vortexAI · puente de Retell

Servicio independiente (FastAPI) que conecta el agente de voz de Retell con vortexAI **sin modificar** `backend/`, `frontend/` ni `DB/`.
Lee el catálogo público `GET {BACKEND_URL}/api/productos`, lo guarda en memoria y responde las funciones del agente.

| Ruta | Para qué sirve |
|---|---|
| `GET /asistente` | Página con el botón de hablar con Vortex |
| `POST /api/crear-llamada` | Crea la llamada web (pide el `ACCESS_CODE`; tiene límites de uso) |
| `POST /retell/buscar-productos` | Función del agente: buscar por palabras clave y filtros |
| `POST /retell/detalle-producto` | Función del agente: detalle de un producto por id |
| `POST /retell/mejores-ofertas` | Función del agente: mayores descuentos |
| `POST /retell/webhook` | Opcional: aviso por Telegram al terminar cada llamada |
| `GET /health` | Despierta el servicio y el catálogo; siempre responde 200 |

Las rutas `/retell/...` verifican la firma `X-Retell-Signature` con tu clave de API.

## Ejecutarlo en tu computador

```powershell
cd retell-bridge
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env        # completa RETELL_API_KEY y ACCESS_CODE
python -m uvicorn main:app --port 8001 --reload
```

Abre http://localhost:8001/asistente. El backend real debe estar corriendo en `BACKEND_URL` (por defecto `http://localhost:8000`).
Si no tienes MySQL, usa el catálogo de mentira (lee el CSV de `Data/`):

```powershell
python -m uvicorn dev.mock_catalogo:app --port 8000
```

## Pruebas

```powershell
pip install pytest
pytest -q
```

## Funciones del agente en Retell

Método **POST** y "Payload: args only" apagado. Los esquemas están en `retell-funciones.md`.

## Azure (App Service Linux, Python)

- Comando de inicio: `python -m uvicorn main:app --host 0.0.0.0 --port 8000`
- Variables de entorno (Configuración → Variables de entorno): `APP_ENV=production`, `BACKEND_URL`, `RETELL_API_KEY`, `RETELL_AGENT_ID`, `ACCESS_CODE` y, si quieres avisos, `TELEGRAM_BOT_TOKEN` y `TELEGRAM_CHAT_ID`.
- En producción el servicio no arranca si faltan `RETELL_API_KEY`, `RETELL_AGENT_ID` o `ACCESS_CODE`.
- Antes de una demostración abre `/health` para despertar el servicio y cargar el catálogo.
- `static/retell-client.js` es el SDK web de Retell (retell-client-js-sdk 3.0.2) empaquetado: no hace falta Node para desplegar.
