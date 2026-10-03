import os
from typing import Any

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import bcrypt

from database import get_db_connection
from import_csv_to_db import import_products_from_csv

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Modelo para el Login ---
class LoginRequest(BaseModel):
    email: str
    password: str


@app.get("/")
def home() -> dict[str, Any]:
    return {"status": "OK", "mensaje": "API de vortexAI en línea"}


@app.get("/api/productos")
def obtener_productos():
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        # Consulta directa sobre la tabla 'products' trayendo los primeros 100 para carga ultrarrápida
        query = """
            SELECT 
                p.id,
                p.source_key,
                p.title AS product_title,
                p.product_page_url,
                c.name AS product_category,
                p.product_image_url,
                p.rating AS product_rating,
                p.total_reviews,
                p.purchased_last_month,
                p.discounted_price,
                p.price,
                p.original_price,
                p.is_sponsored,
                p.has_coupon,
                p.buy_box_availability
            FROM products p
            LEFT JOIN categories c ON c.id = p.category_id
            ORDER BY p.id ASC
            LIMIT 100
        """
        cursor.execute(query)
        rows = cursor.fetchall()

        # Devuelve la lista limpia tal como la espera el Frontend
        return rows

    except Exception as exc:
        return {"error": f"No se pudo consultar la base de datos: {str(exc)}"}


@app.post("/api/importar-datos")
def importar_datos() -> dict[str, Any]:
    try:
        return import_products_from_csv()
    except Exception as exc:
        return {"error": f"Error al importar datos: {str(exc)}"}


# --- Endpoint de Autenticación (/api/login) ---
@app.post("/api/login")
def login(credentials: LoginRequest):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    try:
        # Buscar al usuario por correo
        query = "SELECT id, username, email, password_hash, role_id, is_active FROM users WHERE email = %s"
        cursor.execute(query, (credentials.email,))
        user = cursor.fetchone()
        
        if not user:
            return {"success": False, "message": "Correo o contraseña incorrectos"}
        
        if not user["is_active"]:
            return {"success": False, "message": "La cuenta está desactivada"}
            
        # Verificar la contraseña usando bcrypt
        stored_password_bytes = user["password_hash"].encode('utf-8')
        input_password_bytes = credentials.password.encode('utf-8')
        
        if bcrypt.checkpw(input_password_bytes, stored_password_bytes):
            return {
                "success": True, 
                "message": "Inicio de sesión exitoso",
                "user": {
                    "username": user["username"],
                    "email": user["email"],
                    "role_id": user["role_id"]
                }
            }
        else:
            return {"success": False, "message": "Correo o contraseña incorrectos"}
            
    except Exception as e:
        return {"success": False, "message": f"Error en el servidor: {str(e)}"}
    finally:
        cursor.close()
        conn.close()