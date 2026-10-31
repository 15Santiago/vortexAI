# Funciones personalizadas del agente (Retell)

Para cada una: método POST, "Payload: args only" apagado, hablar durante la ejecución y esperar el resultado activados.
Reemplaza `TU-PUENTE` por el dominio del puente (en Azure: `https://TU-PUENTE.azurewebsites.net`).

## buscar_productos
URL: `https://TU-PUENTE/retell/buscar-productos`
Descripción: Busca productos de electrónica en el catálogo por palabras clave y filtros.
```json
{
  "type": "object",
  "properties": {
    "consulta": { "type": "string", "description": "Palabras clave del producto en inglés, por ejemplo 'wireless earbuds' o 'gaming laptop'." },
    "precio_max": { "type": "number", "description": "Precio máximo en dólares. Omitir si el cliente no lo dijo." },
    "calificacion_min": { "type": "number", "description": "Calificación mínima de 0 a 5." },
    "solo_descuento": { "type": "boolean", "description": "true si pide solo productos con descuento." },
    "orden": { "type": "string", "enum": ["relevancia", "precio_menor", "calificacion", "descuento", "mas_resenas"] },
    "categoria": { "type": "string", "description": "Categoría del sistema en inglés. Usar solo si el cliente la pide." }
  },
  "required": ["consulta"]
}
```

## detalle_producto
URL: `https://TU-PUENTE/retell/detalle-producto`
Descripción: Da el detalle completo de un producto por su id.
```json
{
  "type": "object",
  "properties": {
    "id": { "type": "integer", "description": "Id interno del producto, devuelto por una búsqueda anterior." }
  },
  "required": ["id"]
}
```

## mejores_ofertas
URL: `https://TU-PUENTE/retell/mejores-ofertas`
Descripción: Devuelve los productos con mayor descuento. Para ofertas de un tipo de producto usa consulta.
```json
{
  "type": "object",
  "properties": {
    "consulta": { "type": "string", "description": "Tipo de producto en inglés, por ejemplo 'camera' o 'headphones'. Omitir para ofertas generales." },
    "precio_max": { "type": "number", "description": "Precio máximo en dólares." }
  }
}
```

## Forma de las respuestas
```json
{ "total_encontrados": 57, "coincidencia": "exacta", "resultados": [ { "id": 123, "nombre": "Apple AirPods Pro 2", "precio_usd": 162.24, "descuento_pct": 0, "calificacion": 4.6, "resenas": 35882 } ] }
```
