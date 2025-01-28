import serial
import mysql.connector
import time
from datetime import datetime
import re

# Configuración de umbrales
UMBRAL_TEMPERATURA = 25.0
UMBRAL_GAS = 500

# Banderas para evitar múltiples registros
temp_superado = False
gas_superado = False

# Función para conectar a la base de datos
def connectionBD():
    print("Intentando conectar a la base de datos...")
    try:
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
        if connection.is_connected():
            print("Conexión exitosa a la BD")
            return connection
    except mysql.connector.Error as error:
        print(f"No se pudo conectar: {error}")
        return None

# Función para almacenar la temperatura actual en una tabla específica
def guardar_temperatura_actual(temperatura):
    try:
        fecha_actual = datetime.now()
        cursor.execute(""" 
            INSERT INTO temperatura_actual (temperatura, fecha)
            VALUES (%s, %s)
        """, (temperatura, fecha_actual))
        db_connection.commit()
        print(f"Temperatura actual guardada: {fecha_actual}, {temperatura}°C")
    except mysql.connector.Error as error:
        print(f"Error al guardar temperatura actual: {error}")

# Función para eliminar la última temperatura guardada
def eliminar_temperatura_actual():
    try:
        cursor.execute("DELETE FROM temperatura_actual WHERE id = (SELECT MAX(id) FROM temperatura_actual)")
        db_connection.commit()
        print("Temperatura actual eliminada.")
    except mysql.connector.Error as error:
        print(f"Error al eliminar temperatura actual: {error}")

# Funciones para guardar otros datos en la base de datos (gas, RFID, etc.)
def guardar_datos_gas(rango):
    try:
        fecha_actual = datetime.now().strftime('%Y-%m-%d')
        hora_actual = datetime.now().strftime('%H:%M:%S')
        cursor.execute(""" 
            INSERT INTO sensores_humo (rango, fecha, hora)
            VALUES (%s, %s, %s)
        """, (rango, fecha_actual, hora_actual))
        db_connection.commit()
        print(f"Gas guardado: {fecha_actual} {hora_actual}, Rango: {rango}")
    except mysql.connector.Error as error:
        print(f"Error al guardar datos de gas: {error}")

# Configuración de conexiones
db_connection = connectionBD()
cursor = db_connection.cursor() if db_connection else None

# Configuración de los puertos seriales
try:
    ser_rfid = serial.Serial('COM4', 9600, timeout=1)  # Puerto para el Arduino RFID
    ser_sensor = serial.Serial('COM3', 9600, timeout=1)  # Puerto para el Arduino de sensores
    time.sleep(2)
    print("Conexión serie establecida.")
except serial.SerialException as error:
    print(f"Error al conectar con los puertos seriales: {error}")
    ser_rfid = ser_sensor = None

# Loop principal
try:
    while ser_rfid and ser_sensor and ser_rfid.is_open and ser_sensor.is_open:
        # Leer datos de ambos Arduinos
        if ser_rfid.in_waiting > 0:
            linea_rfid = ser_rfid.readline().decode('utf-8').strip()
            print(f"Datos RFID recibidos: {linea_rfid}")
            if "uid de la tarjeta:" in linea_rfid.lower():
                uid = linea_rfid.split(":")[1].strip().lower()
                print(f"UID procesado: {uid}")
                # Consultar en la base de datos
                cursor.execute("SELECT * FROM usuarios WHERE LOWER(tarjeta) = %s", (uid,))
                result = cursor.fetchone()
                estado_acceso = "permitido" if result else "denegado"
                cedula_usuario = result[1] if result else None
                guardar_datos_rfid(uid, estado_acceso, cedula_usuario)
                if result:
                    ser_rfid.write(b'1')
                else:
                    ser_rfid.write(b'0')

        if ser_sensor.in_waiting > 0:
            linea_sensor = ser_sensor.readline().decode('utf-8').strip()
            print(f"Datos de sensores recibidos: {linea_sensor}")

            # Validar formato con expresión regular
            match = re.match(r"temperatura:\s*([\d.]+),\s*gas:\s*(\d+)", linea_sensor, re.IGNORECASE)
            if match:
                try:
                    temperatura = float(match.group(1))
                    gas = int(match.group(2))

                    # Solo guardar la temperatura actual cuando la temperatura supera el umbral
                    if temperatura > UMBRAL_TEMPERATURA:
                        guardar_temperatura_actual(temperatura)
                    else:
                        # Eliminar la temperatura actual si cae debajo del umbral
                        eliminar_temperatura_actual()

                    # Solo guardar el primer registro cuando el gas supera el umbral
                    if gas > UMBRAL_GAS:
                        if not gas_superado:  # Solo registrar si no se ha registrado antes
                            guardar_datos_gas(gas)
                            gas_superado = True
                    else:
                        gas_superado = False  # Reinicia la bandera si vuelve a valores normales

                except ValueError as e:
                    print(f"Error al convertir valores: {e}")
            else:
                print("Formato de datos no válido.")
        time.sleep(1)
except KeyboardInterrupt:
    print("\nFinalizando programa.")
finally:
    if cursor:
        cursor.close()
    if db_connection:
        db_connection.close()
    if ser_rfid and ser_rfid.is_open:
        ser_rfid.close()
    if ser_sensor and ser_sensor.is_open:
        ser_sensor.close()
    print("Conexiones cerradas.")
