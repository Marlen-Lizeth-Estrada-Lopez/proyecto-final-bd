import psycopg2

def get_connection():
    conn = psycopg2.connect(
        host="localhost",
        port=5432,
        database="prueba2proyectobd",
        user="postgres",
        password="postgres123"
    )
    return conn

if __name__ == "__main__":
    try:
        conn = get_connection()
        print("Conexión exitosa")
        conn.close()
    except Exception as e:
        print("Error:", e)