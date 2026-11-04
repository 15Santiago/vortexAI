import logging
import json
from app.infrastructure.database import get_db_connection
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report

def auditar_calidad_catalogo():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        print("Iniciando auditoría de calidad del catálogo con Machine Learning...")
        cursor.execute(
            """
            SELECT p.id, p.title, c.name AS category
            FROM products p
            JOIN categories c ON c.id = p.category_id
            WHERE p.title IS NOT NULL AND c.name IS NOT NULL
            """
        )
        rows = cursor.fetchall()
        if len(rows) < 50:
            print("No hay suficientes datos para entrenar el modelo de auditoría.")
            return

        titles = [row["title"] for row in rows]
        categories = [row["category"] for row in rows]
        ids = [row["id"] for row in rows]

        # Vectorización TF-IDF
        print("Vectorizando títulos con TF-IDF...")
        vectorizer = TfidfVectorizer(stop_words="english", max_features=5000)
        X = vectorizer.fit_transform(titles)
        y = categories

        # Train/Test Split para métricas
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.2, random_state=42
        )

        print("Entrenando modelo de Regresión Logística...")
        model = LogisticRegression(max_iter=1000)
        model.fit(X_train, y_train)

        # Reporte de métricas
        y_pred = model.predict(X_test)
        print("\n=== REPORTE DE MÉTRICAS DEL AUDITOR (TEST SET) ===")
        print(classification_report(y_test, y_pred, zero_division=0))

        # Auditoría completa del catálogo
        print("\nDetectando anomalías y desalineaciones de categorías...")
        all_preds = model.predict(X)

        anomalias_detectadas = []
        for i, predicted_cat in enumerate(all_preds):
            actual_cat = categories[i]
            if predicted_cat != actual_cat:
                anomalias_detectadas.append({
                    "product_id": ids[i],
                    "titulo": titles[i],
                    "categoria_actual": actual_cat,
                    "categoria_sugerida_ml": predicted_cat
                })

        print(f"\n[Resultado] Total de productos analizados: {len(rows)}")
        print(f"[Resultado] Anomalías de categorización detectadas: {len(anomalias_detectadas)}")

        # Guardar reporte de auditoría en JSON para evidencias del proyecto
        reporte_path = "reporte_auditoria_categorias.json"
        with open(reporte_path, "w", encoding="utf-8") as f:
            json.dump(anomalias_detectadas, f, ensure_ascii=False, indent=4)
        print(f"Reporte de auditoría guardado exitosamente en '{reporte_path}'.")

    finally:
        cursor.close()
        conn.close()

if __name__ == "__main__":
    auditar_calidad_catalogo()