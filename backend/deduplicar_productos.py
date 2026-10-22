import os
from collections import defaultdict

from dotenv import load_dotenv
import mysql.connector
from mysql.connector import Error

load_dotenv(os.path.join(os.path.dirname(__file__), '.env'))


def get_conn():
    return mysql.connector.connect(
        host=os.getenv('DB_HOST', 'localhost'),
        port=int(os.getenv('DB_PORT', '3306')),
        user=os.getenv('DB_USER', 'root'),
        password=os.getenv('DB_PASSWORD', ''),
        database=os.getenv('DB_NAME', 'vortexai'),
        charset='utf8mb4',
        autocommit=True,
    )


def dedupe_products(batch_size=25):
    conn = get_conn()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute('SET SESSION innodb_lock_wait_timeout = 30')
        cursor.execute(
            "SELECT LOWER(TRIM(title)) AS norm_title, GROUP_CONCAT(id ORDER BY id) AS ids FROM products GROUP BY LOWER(TRIM(title)) HAVING COUNT(*) > 1"
        )
        groups = cursor.fetchall()
        print(f'FOUND_DUPLICATE_GROUPS={len(groups)}')

        removed = 0
        for group_index, group in enumerate(groups, start=1):
            ids = [int(part) for part in str(group['ids']).split(',') if part]
            if len(ids) <= 1:
                continue

            duplicate_ids = ids[1:]
            if not duplicate_ids:
                continue

            for batch_start in range(0, len(duplicate_ids), batch_size):
                batch = duplicate_ids[batch_start:batch_start + batch_size]
                if not batch:
                    continue

                placeholders = ', '.join(['%s'] * len(batch))
                cursor.execute(
                    f'DELETE FROM product_observations WHERE product_id IN ({placeholders})',
                    tuple(batch),
                )
                cursor.execute(
                    f'DELETE FROM product_images WHERE product_id IN ({placeholders})',
                    tuple(batch),
                )
                cursor.execute(
                    f'DELETE FROM products WHERE id IN ({placeholders})',
                    tuple(batch),
                )
                conn.commit()
                removed += len(batch)

                print(f'GROUP={group_index} BATCH={batch_start // batch_size + 1} REMOVED_IN_BATCH={len(batch)} TOTAL_REMOVED={removed}')

        cursor.execute('SELECT COUNT(*) AS total FROM products')
        remaining = cursor.fetchone()['total']
        cursor.execute('SELECT COUNT(*) AS c FROM (SELECT LOWER(TRIM(title)) AS t FROM products GROUP BY LOWER(TRIM(title)) HAVING COUNT(*) > 1) d')
        duplicate_titles = cursor.fetchone()['c']

        print(f'REMOVED={removed}')
        print(f'REMAINING_PRODUCTS={remaining}')
        print(f'DUPLICATE_TITLES_AFTER={duplicate_titles}')
        return {'removed': removed, 'remaining_products': remaining, 'duplicate_titles_after': duplicate_titles}
    except Error as exc:
        conn.rollback()
        raise RuntimeError(f'Error deduplicando productos: {exc}') from exc
    finally:
        cursor.close()
        conn.close()


if __name__ == '__main__':
    print(dedupe_products())
