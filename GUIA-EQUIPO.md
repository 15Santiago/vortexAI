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
    pnpm dev
Abre http://localhost:5173

## 5. Asistente de voz (puerto 8001)
Cada integrante debe crear su propio archivo local `retell-bridge/.env` a partir de `retell-bridge/.env.example` y configurar allí sus credenciales. No compartas ni subas ese archivo.
Abre otra terminal en la raíz del repositorio y ejecuta:
    cd retell-bridge
    copy .env.example .env
    python -m venv .venv
    .\.venv\Scripts\Activate.ps1
    pip install -r requirements.txt
    python -m uvicorn main:app --port 8001
Abre http://localhost:8001/asistente, escribe el ACCESS_CODE que configuraste en tu `.env`, pulsa el círculo y permite el micrófono. El backend debe estar corriendo en el puerto 8000.

## Si algo falla
- La página de voz muestra un panel "Detalles técnicos": copia su contenido y compártelo con el equipo.
- Si el puente no encuentra productos, revisa que el backend esté corriendo y que la importación haya terminado.
- Para el catálogo sin MySQL: python -m uvicorn dev.mock_catalogo:app --port 8000 (dentro de retell-bridge).

## Reglas del equipo
- El repositorio debe seguir PRIVADO.
- No subir backend/.env ni ningún otro archivo .env.
- No compartir la clave de Retell fuera del equipo.
- Al terminar el proyecto: eliminar la clave en Retell (Settings > API Keys) y crear otra.
