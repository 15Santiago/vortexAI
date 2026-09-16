import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import pandas as pd

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Construye la ruta absoluta para evitar problemas de carpetas en Windows
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_PATH = os.path.join(BASE_DIR, "..", "Data", "amazon_products_sales_data_cleaned.csv")
@app.get("/")
def home():
    return {"status": "OK", "mensaje": "API de vortexAI en línea"}

@app.get("/api/productos")
def obtener_productos():
    if not os.path.exists(DATA_PATH):
        return {"error": f"No se encontró el archivo en la ruta: {DATA_PATH}"}
    
    try:
        df = pd.read_csv(DATA_PATH)
        df = df.fillna("")
        primeros_registros = df.head(10).to_dict(orient="records")
        return {"total": len(df), "productos": primeros_registros}
    except Exception as e:
        return {"error": f"Error al leer el archivo: {str(e)}"}