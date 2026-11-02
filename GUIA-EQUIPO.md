# Guía del equipo: vortexAI completo en tu computador

Esta guía deja funcionando las tres piezas del proyecto: base de datos + backend, frontend y el asistente de voz (puente de Retell).

## Requisitos
- Git, Python 3.10 o superior, Node 22 con pnpm (npm i -g pnpm), MySQL 8 o superior y VS Code.
- Navegador Chrome o Edge (sin VPN ni bloqueadores activos para probar la voz).

## 1. Descargar el proyecto
    git clone https://github.com/15Santiago/vortexAI.git
    cd vortexAI
    git checkout feature/retell-bridge

## 2. Base de datos
    mysql -u root -p < DB/schema.sql

## 3. Backend (puerto 8000)
    cd backend
    python -m venv venv
    .\venv\Scripts\Activate.ps1
    pip install -r requirements.txt
    copy .env.example .env
Edita backend/.env y pon TU propia contraseña de MySQL en DB_PASSWORD (esta contraseña es de cada computador y NO se comparte ni se sube a Git). Luego:
    python -m uvicorn main:app --port 8000
Abre http://localhost:8000/docs y ejecuta POST /api/importar-datos para cargar los productos (tarda varios minutos; no cierres el servidor).
Mantén el backend ejecutándose y abre otra terminal en la raíz del repositorio para continuar.

## 4. Frontend (puerto 5173)
Abre otra terminal en la raíz del repositorio y ejecuta:
    cd frontend
    pnpm install
    copy .env.example .env.local
Comprueba que `.env.local` tenga `VITE_ASSISTANT_API_URL=http://localhost:8001` y `VITE_ASSISTANT_ACCESS_CODE=vortex2026`. Este archivo es local, está ignorado por Git y Vite debe reiniciarse al cambiar variables `VITE_`.
    pnpm dev
Abre http://localhost:5173 e inicia sesión: el widget de voz aparece en la esquina inferior derecha solo cuando hay una sesión activa.

## 5. Asistente de voz (puerto 8001)
Cada integrante debe crear su propio archivo local `retell-bridge/.env` a partir de `retell-bridge/.env.example` y configurar allí sus credenciales. No compartas ni subas ese archivo.
Abre otra terminal en la raíz del repositorio y ejecuta:
    cd retell-bridge
    copy .env.example .env
    python -m venv .venv
    .\.venv\Scripts\Activate.ps1
    pip install -r requirements.txt
    python -m uvicorn main:app --port 8001
En `retell-bridge/.env`, configura `ACCESS_CODE=vortex2026` y `CORS_ORIGINS=http://localhost:5173,http://127.0.0.1:5173`. El backend debe estar corriendo en el puerto 8000. Inicia sesión en el frontend y usa el widget flotante; la página `/asistente` del puente queda disponible como respaldo.

El frontend obtiene la URL del puente de `VITE_ASSISTANT_API_URL` (por defecto, el host actual en el puerto 8001) y la clave visible del widget de `VITE_ASSISTANT_ACCESS_CODE`. En Azure, define ambas variables durante el build del frontend, apunta la URL a la dirección HTTPS del puente y agrega la URL HTTPS del frontend a `CORS_ORIGINS` del puente. El micrófono requiere HTTPS en producción; `localhost` también es un contexto seguro para desarrollo. Si el hosting añade `Permissions-Policy`, permite `microphone=(self)`.

## Si algo falla
- El widget muestra "Detalles técnicos" con eventos locales sin tokens ni claves; la página `/asistente` del puente sigue disponible como respaldo.
- Si el puente no encuentra productos, revisa que el backend esté corriendo y que la importación haya terminado.
- Para el catálogo sin MySQL: python -m uvicorn dev.mock_catalogo:app --port 8000 (dentro de retell-bridge).

## Reglas del equipo
- El repositorio debe seguir PRIVADO.
- No subir backend/.env ni ningún otro archivo .env.
- No compartir la clave de Retell fuera del equipo.
- Al terminar el proyecto: eliminar la clave en Retell (Settings > API Keys) y crear otra.

## Puesta en marcha integrada y prueba sin voz

Para probar la integración local, mantén tres terminales abiertas desde la raíz del repositorio:

1. **Backend (8000):** activa el entorno virtual de `backend/` y ejecuta `python -m uvicorn main:app --port 8000`.
2. **Puente Retell (8001):** activa `.venv` dentro de `retell-bridge/` y ejecuta `python -m uvicorn main:app --port 8001`.
3. **Frontend (5173):** dentro de `frontend/`, ejecuta `pnpm dev`.

En una cuarta terminal, inicia un túnel temporal al puente:

```powershell
cloudflared tunnel --url http://localhost:8001
```

Conserva abierta esa terminal. Cloudflare imprime una URL HTTPS pública; su dirección temporal cambia si el túnel se detiene y se crea de nuevo. Usa la URL vigente para registrar las herramientas y ejecutar el humo:

```powershell
cd retell-bridge
.\.venv\Scripts\python.exe scripts\registrar_funciones.py --url https://URL-VIGENTE.trycloudflare.com --dry-run
.\.venv\Scripts\python.exe scripts\registrar_funciones.py --url https://URL-VIGENTE.trycloudflare.com
.\.venv\Scripts\python.exe scripts\prueba_humo.py --puente http://localhost:8001 --publica https://URL-VIGENTE.trycloudflare.com
```

Cada integrante debe configurar su propio `RETELL_API_KEY` y `RETELL_AGENT_ID` en su `retell-bridge/.env`; no copie credenciales de otro integrante ni las incluya en `.env.example`. El registro puede crear un agente de reemplazo si el actual está publicado y actualiza el `RETELL_AGENT_ID` local cuando lo hace.

El humo simula los webhooks de Retell sin audio. Para esa simulación, el puente local debe tener `DEV_SKIP_SIGNATURE=true` en `retell-bridge/.env` y `APP_ENV` distinto de `production`; reinicia el puente después del cambio, ejecuta la prueba y restaura inmediatamente `DEV_SKIP_SIGNATURE=false`, reiniciando de nuevo el puente. No habilites esa opción en producción ni expongas el puente sin el túnel/control de acceso correspondiente. Si no puedes cambiar temporalmente el ajuste, el humo reportará bloqueada la simulación; no alterará el `.env`.
