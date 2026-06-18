# COOVALLUNA - Sistema de Gestión para Cooperativa de Ahorro y Crédito

Proyecto final del curso de Bases de Datos Relacionales.

## Requisitos
- Python 3.10+
- PostgreSQL 14+

## Instalación

1. Clonar el repositorio:
   ```bash
   git clone https://github.com/Marlen-Lizeth-Estrada-Lopez/proyecto-final-bd.git
   cd proyecto-final-bd
    ```
2. Instalar dependencias:

```bash
pip install -r requirements.txt
```

3. Crear la base de datos en PostgreSQL

4. Ejecutar los scripts SQL (en orden)

5. Configurar conexión a BD en `bd.py` con tus credenciales.
    ```
    def get_connection():
        return psycopg2.connect(
            host="localhost",
            database="coovalluna",
            user="postgres",
            password="tu_contraseña"
        )
    ```
6. Ejecutar la aplicación `app.py`

7. Acceder a: http://127.0.0.1:5000

# Accesos de prueba
- Admin: admin / admin123
- Asesor: asesor1 / asesor123
- Asociado: asociado1 / asoc123





