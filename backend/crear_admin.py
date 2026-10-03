import bcrypt
from database import get_db_connection

def create_admin_user():
    # Credenciales proporcionadas
    username = "admin"
    full_name = "Administrador Vortex"
    email = "admin@vortexai.local"
    plain_password = "_1VVvf76FmEg79Di3SkWzKbRwdRwJ8ij"
    
    # Generar el hash seguro con bcrypt
    password_bytes = plain_password.encode('utf-8')
    salt = bcrypt.gensalt()
    hashed_password = bcrypt.hashpw(password_bytes, salt).decode('utf-8')

    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        # Insertar el usuario administrador incluyendo full_name y username
        query = """
            INSERT INTO users (username, full_name, email, password_hash, role_id, is_active)
            VALUES (%s, %s, %s, %s, 1, 1)
        """
        cursor.execute(query, (username, full_name, email, hashed_password))
        conn.commit()
        print("¡Usuario administrador creado e insertado con éxito en la base de datos!")
    except Exception as e:
        print(f"Error al crear el usuario (es posible que ya exista): {e}")
    finally:
        cursor.close()
        conn.close()

if __name__ == "__main__":
    create_admin_user()