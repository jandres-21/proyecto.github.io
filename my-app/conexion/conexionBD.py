

import mysql.connector

def connectionBD():
    print("ENTRO A LA CONEXION")
    try:
        # Conexión con la base de datos utilizando la URL proporcionada
        connection = mysql.connector.connect(
            host="34.57.72.162",      # Host de la base de datos
            port=3306,                           # Puerto
            user="root",                          # Usuario
            passwd="HfvkMwoYEeFwlmqQJbRZAXnyaXciAojX",  # Contraseña
            database="railway",                   # Base de datos
            charset='utf8mb4',                    # Codificación de caracteres
            collation='utf8mb4_unicode_ci',       # Colación
            raise_on_warnings=True                # Levanta errores si los hay
        )
        
        # Verificando la conexión
        if connection.is_connected():
            print("Conexión exitosa a la BD")
            return connection

    except mysql.connector.Error as error:
        print(f"No se pudo conectar: {error}")

# Llamada a la función para probar la conexión
connectionBD()
