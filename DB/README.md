# Esquema de base de datos

El esquema está diseñado para MySQL 8.0+ y representa un catálogo consultable. No incluye carritos, compras, pedidos ni pagos porque esas funciones no forman parte del alcance actual.

## Tablas principales

- `roles` y `users`: perfiles `usuario` y `administrador`. El registro solicita correo electrónico, nombre completo y contraseña; la aplicación debe guardar la contraseña únicamente como `password_hash` usando un algoritmo como Argon2id o bcrypt.
- `categories`: catálogo de categorías sin repetir nombres.
- `products`: identidad estable del producto. El ASIN se extrae del segmento `/dp/{ASIN}` de la URL de Amazon, ya que la URL completa contiene parámetros de rastreo variables. Como hay 2.069 filas sin `product_page_url`, `source_key` debe ser un SHA-256 del ASIN cuando exista y, en caso contrario, del título normalizado junto con la imagen.
- `product_images`: imágenes asociadas a cada producto.
- `product_observations`: valores observados en cada captura del dataset. Permite conservar el historial de precio, rating, reseñas, ventas estimadas, promociones y disponibilidad para consultas estadísticas.

## Normalización del CSV

El CSV original mezcla identidad del producto, categoría, imagen y métricas temporales en una sola fila. El proceso de carga debe:

1. Extraer y normalizar el ASIN desde `product_page_url` después de decodificar URLs con segmentos como `%2Fdp%2F`; cuando falte la URL, generar `source_key` con el título normalizado y la imagen.
2. Insertar o localizar la categoría en `categories`.
3. Insertar o actualizar la identidad en `products`.
4. Insertar la imagen en `product_images`.
5. Convertir cadenas vacías a `NULL` y guardar las métricas de la fila en `product_observations`.
6. Convertir `is_sponsored` a booleano (`Sponsored` = `TRUE`, `Organic` = `FALSE`).
7. Convertir fechas, precios y porcentajes a sus tipos SQL correspondientes.

Los valores como `has_coupon`, `is_best_seller`, `buy_box_availability` y `sustainability_tags` se conservan como atributos de la observación porque describen el estado del producto en el momento de la captura y no una propiedad permanente del producto.