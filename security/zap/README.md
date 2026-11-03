# OWASP ZAP

Este escaneo usa copias portables locales de OWASP ZAP y Temurin JRE (sin Docker ni instalación
global) y guarda un informe HTML en `security/zap/reports/vortexai-dast.html`. Los binarios quedan
en `security/zap/tools/`, ignorados por Git, y no se agregan como dependencias de Node.

## Preparación inicial

Los paquetes portables se descargan de los releases oficiales de ZAP y Adoptium. Verifica los
SHA-256 publicados antes de extraerlos en `security/zap/tools/`.

Para otras rutas, se puede definir `ZAP_PATH` con una ruta completa a `zap.bat`.

El script inicia y cierra una instancia aislada de ZAP en el puerto local `8090`, y conserva sus
datos bajo `security/zap/.zap-data/`.

## Ejecutar

Desde la raíz del repositorio:

```powershell
.\security\zap\run-zap.ps1
```

También se puede ejecutar desde `frontend` con `pnpm run security:dast`.

El frontend debe estar disponible en `http://localhost:5173` y el backend en
`http://localhost:8000`.

El escaneo importa las rutas de OpenAPI y rastrea el frontend y la API con el Spider y las reglas
pasivas. No inicia el escáner activo ni intenta explotar vulnerabilidades. Las rutas que requieren
inicio de sesión necesitan una configuración autenticada adicional y no se cubren con este reporte.
