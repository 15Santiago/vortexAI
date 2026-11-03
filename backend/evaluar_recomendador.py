
import sys
import io


sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

import random
from collections import defaultdict
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import linear_kernel
from sklearn.cluster import MiniBatchKMeans
from database import get_db_connection

K = 8                      # cuántas sugerencias se muestran
SEED = 42
SIM_TRIALS = 300           # sesiones simuladas
POOL_PER_CATEGORY = 1500   # igual que en la app
RECENCY_DECAY = 0.85       # igual que en la app
MAX_HISTORY = 6            # igual que en la app
NUM_CLUSTERS = 50          # Cantidad de grupos (K-Means)

def normalize(text):
    return " ".join((text or "").lower().split())

def title_key(text):
    return " ".join(normalize(text).split()[:6])

def load_data():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute(
            """
            SELECT p.id, p.title, p.category_id, c.name AS category
            FROM products p
            LEFT JOIN categories c ON c.id = p.category_id
            """
        )
        products = cursor.fetchall()
        try:
            cursor.execute(
                "SELECT user_id, product_id, viewed_at FROM user_product_views ORDER BY user_id, viewed_at"
            )
            views = cursor.fetchall()
        except Exception:
            views = []
        return products, views
    finally:
        cursor.close()
        conn.close()

def build_pool(products):
    by_category = defaultdict(list)
    for product in products:
        by_category[product["category_id"]].append(product)
    pool = []
    for items in by_category.values():
        items.sort(key=lambda row: row["id"], reverse=True)
        pool.extend(items[:POOL_PER_CATEGORY])
    return pool

def recommend_with_clusters(history, candidates, matrix, labels, k=K):
    """Recomendador potenciado con K-Means: prioriza productos del mismo clúster que el historial."""
    weights = np.array([RECENCY_DECAY ** i for i in range(len(history))])
    
    # Identificar los clústeres a los que pertenecen los productos recientes del usuario
    history_clusters = set(labels[history])
    
    # Similitud base coseno con decaimiento
    similarity = (linear_kernel(matrix[history], matrix[candidates]) * weights[:, None]).max(axis=0)
    
    # Bono de afinidad si el candidato pertenece al mismo clúster temático
    cluster_bonus = np.array([1.2 if labels[c] in history_clusters else 1.0 for c in candidates])
    similarity = similarity * cluster_bonus

    order = np.argsort(-similarity)
    seen = {title_key(pool[i]["title"]) for i in history}
    chosen = []
    for position in order:
        index = candidates[position]
        key = title_key(pool[index]["title"])
        if key in seen:
            continue
        seen.add(key)
        chosen.append(index)
        if len(chosen) >= k:
            break
    return chosen

def candidates_for(history):
    categories = {pool[i]["category_id"] for i in history}
    history_set = set(history)
    return [i for i in range(len(pool)) if pool[i]["category_id"] in categories and i not in history_set]

def evaluate_simulated(matrix, labels, rng):
    groups = defaultdict(list)
    for index, product in enumerate(pool):
        first = normalize(product["title"]).split()[:1]
        brand = first[0] if first and first[0].isalpha() and len(first[0]) > 2 else None
        if brand:
            groups[(product["category_id"], brand)].append(index)
    usable = []
    for members in groups.values():
        unique = {}
        for index in members:
            unique.setdefault(title_key(pool[index]["title"]), index)
        if len(unique) >= 6:
            usable.append(list(unique.values()))
    if not usable:
        return 0, 0, 0.0
    hits = random_hits = total = 0
    for _ in range(SIM_TRIALS):
        sample = rng.sample(rng.choice(usable), 5)
        held_out, history = sample[0], sample[1:]
        candidates = candidates_for(history)
        if held_out not in set(candidates):
            continue
        total += 1
        hits += held_out in recommend_with_clusters(history, candidates, matrix, labels)
        random_hits += held_out in set(rng.sample(candidates, min(K, len(candidates))))
    return hits, total, (random_hits / total if total else 0.0)

if __name__ == "__main__":
    rng = random.Random(SEED)
    print("Cargando datos del catalogo...")
    products, views = load_data()
    pool = build_pool(products)
    
    print("Calculando vectores TF-IDF...")
    texts = [f"{p['title'] or ''} {p['category'] or ''}" for p in pool]
    matrix = TfidfVectorizer(stop_words="english", max_features=5000).fit_transform(texts)
    
    print(f"Aplicando K-Means Clustering (agrupando en {NUM_CLUSTERS} clústeres temáticos)...")
    kmeans = MiniBatchKMeans(n_clusters=NUM_CLUSTERS, random_state=SEED, batch_size=1024, n_init='auto')
    labels = kmeans.fit_predict(matrix)
    
    print(f"Productos en el grupo de candidatos: {len(pool)}")
    
    hits, total, random_rate = evaluate_simulated(matrix, labels, rng)
    print("\n== Evaluación CON CLUSTERING (K-Means) ===")
    if total:
        print(f"Casos: {total} | Aciertos@{K}: {hits} | Hit rate@{K}: {hits / total:.1%}")
        print(f"Referencia, sugerir al azar: {random_rate:.1%}")
    else:
        print("No se pudieron armar sesiones simuladas.")