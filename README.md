# vortexAI

## Reglas de desarrollo

1. Los paquetes de JavaScript se instalarán obligatoriamente mediante `pnpm`.
2. El backend se desarrollará con FastAPI utilizando Python, y sus dependencias se instalarán mediante `pip`.
3. La base de datos será MySQL.

## Seguridad

- Las contraseñas se almacenan con bcrypt; los hashes scrypt creados anteriormente se actualizan a bcrypt después de un inicio de sesión válido.
- Las consultas que reciben valores externos deben usar parámetros SQL. No se deben filtrar comillas u otros caracteres válidos como sustituto de consultas parametrizadas.
- Las sesiones usan cookies `HttpOnly`, `SameSite=Lax`, caducidad y almacenamiento del token en forma de hash.
- En producción configura `APP_ENV=production`, `CORS_ORIGINS` con dominios HTTPS explícitos, `DB_SSL_CA`, `DB_NAME`, una contraseña y un usuario MySQL de aplicación con permisos mínimos.
- Bcrypt no cifra datos de catálogo ni permite recuperarlos. Para proteger la base completa en reposo, habilita cifrado de disco o cifrado de tablespaces en el servidor MySQL y protege las claves fuera de la base.