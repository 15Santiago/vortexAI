import os
import pandas as pd
from database import get_db_connection

def import_products_from_csv():
    csv_path = os.path.join(os.path.dirname(__file__), "..", "Data", "amazon_products_sales_data_cleaned.csv")

    print(f"Buscando archivo en: {os.path.abspath(csv_path)}")

    if not os.path.exists(csv_path):
        print("❌ ERROR: El archivo CSV no existe en esa ruta.")
        return

    print("✅ Archivo CSV encontrado. Leyendo datos...")
    df = pd.read_csv(csv_path)
    # Convertir valores NaN / NaT de pandas a None explícito para Python y MySQL
    df = df.astype(object).where(pd.notnull(df), None)
    print(f"Total de filas encontradas en el CSV: {len(df)}")

    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        print("✅ Conexión a la base de datos exitosa.")

        # 1. Obtener categorías únicas del CSV e insertarlas en la tabla categories
        unique_categories = [c for c in df['product_category'].dropna().unique() if c is not None]
        print(f"Categorías únicas encontradas: {len(unique_categories)}")

        category_map = {}
        for cat_name in unique_categories:
            cursor.execute("INSERT INTO categories (name) VALUES (%s) ON DUPLICATE KEY UPDATE id=LAST_INSERT_ID(id);", (cat_name,))
            category_map[cat_name] = cursor.lastrowid
        
        # Categoría por defecto si el producto no tiene
        cursor.execute("INSERT INTO categories (name) VALUES (%s) ON DUPLICATE KEY UPDATE id=LAST_INSERT_ID(id);", ('Sin Categoría',))
        default_cat_id = cursor.lastrowid

        conn.commit()
        print("✅ Categorías procesadas e insertadas correctamente.")

        # 2. Insertar los productos con source_key y asin únicos por fila
        query = """
            INSERT INTO products (source_key, asin, title, category_id, product_page_url)
            VALUES (%s, %s, %s, %s, %s)
        """

        data = []
        for idx, row in df.iterrows():
            cat_name = row.get('product_category')
            cat_id = category_map.get(cat_name, default_cat_id)
            title_val = str(row.get('product_title') or 'Sin título')[:255]
            
            raw_url = row.get('product_page_url')
            url_val = str(raw_url) if raw_url is not None else None
            
            unique_source_key = f"AMAZON_{idx + 1}"
            unique_asin = f"ASIN_{idx + 1}"

            data.append((unique_source_key, unique_asin, title_val, cat_id, url_val))

        print("Cargando los registros en MySQL...")
        cursor.executemany(query, data)
        conn.commit()

        print(f"🎉 ¡Éxito! Se procesaron correctamente {cursor.rowcount} registros.")
        cursor.close()
        conn.close()

    except Exception as e:
        print(f"❌ ERROR de MySQL: {e}")

if __name__ == "__main__":
    import_products_from_csv()