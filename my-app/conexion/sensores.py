import serial
import mysql.connector
from datetime import datetime
import time
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
            host="junction.proxy.rlwy.net",
            port=21594,
            user="root",
            passwd="HfvkMwoYEeFwlmqQJbRZAXnyaXciAojX",
            database="railway",
            charset='utf8mb4',
            collation='utf8mb4_unicode_ci',
            raise_on_warnings=True
        )
        if connection.is_connected():
            print("Conexión exitosa a la BD")
            return connection
    except mysql.connector.Error as error:
        print(f"No se pudo conectar: {error}")
        return None

# Configuración de conexiones
db_connection = connectionBD()
cursor = db_connection.cursor() if db_connection else None

# Configuración del puerto serial
try:
    ser = serial.Serial('COM3', 9600)  # Cambia 'COM3' según tu puerto
    time.sleep(2)
    print("Conexión serie establecida.")
except serial.SerialException as error:
    print(f"Error al conectar con el puerto serial: {error}")
    ser = None

# Funciones para guardar datos en la base de datos
def guardar_datos_temperatura(temperatura):
    try:
        fecha_actual = datetime.now()
        ubicacion = "Maqueta Data Center"
        cursor.execute("""
            INSERT INTO temperatura (fecha, temperatura, ubicacion)
            VALUES (%s, %s, %s)
        """, (fecha_actual, temperatura, ubicacion))
        db_connection.commit()
        print(f"Temperatura guardada: {fecha_actual}, {temperatura}°C, Ubicación: {ubicacion}")
    except mysql.connector.Error as error:
        print(f"Error al guardar temperatura: {error}")

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

# Loop principal
try:
    while ser and ser.is_open:
        if ser.in_waiting > 0:
            linea = ser.readline().decode('utf-8').strip()
            print(f"Datos recibidos: {linea}")

            # Validar formato con expresión regular
            match = re.match(r"temperatura:\s*([\d.]+),\s*gas:\s*(\d+)", linea, re.IGNORECASE)
            if match:
                try:
                    temperatura = float(match.group(1))
                    gas = int(match.group(2))

                    # Validar temperatura y registrar solo la primera vez que supere el umbral
                    if temperatura > UMBRAL_TEMPERATURA:
                        if not temp_superado:  # Solo registrar si no se ha registrado antes
                            guardar_datos_temperatura(temperatura)
                            temp_superado = True
                    else:
                        temp_superado = False  # Reinicia la bandera si vuelve a valores normales

                    # Validar gas y registrar solo la primera vez que supere el umbral
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
    if ser and ser.is_open:
        ser.close()
    print("Conexiones cerradas.")
