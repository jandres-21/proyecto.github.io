import serial
import threading
import mysql.connector
from datetime import datetime
import re
import time

# Configuración de los puertos seriales
PUERTO_ARDUINO_1 = 'COM4'  # Cambia según tu configuración
PUERTO_ARDUINO_2 = 'COM3'

BAUD_RATE = 9600

# Umbrales
UMBRAL_TEMPERATURA = 25.0
UMBRAL_GAS = 500

# Función para conectar a la base de datos
def connectionBD():
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

db_connection = connectionBD()
cursor = db_connection.cursor() if db_connection else None

# Función para manejar datos del primer Arduino
def manejar_arduino_1():
    try:
        ser1 = serial.Serial(PUERTO_ARDUINO_1, BAUD_RATE, timeout=1)
        time.sleep(2)
        print("Arduino 1 conectado.")
        while True:
            if ser1.in_waiting > 0:
                linea = ser1.readline().decode('utf-8').strip()
                print(f"Arduino 1: {linea}")
                # Procesa los datos aquí (por ejemplo, UID de tarjetas)
                if "uid de la tarjeta:" in linea.lower():
                    procesar_uid(linea)
    except serial.SerialException as error:
        print(f"Error en Arduino 1: {error}")
    finally:
        if ser1.is_open:
            ser1.close()

# Función para manejar datos del segundo Arduino
def manejar_arduino_2():
    try:
        ser2 = serial.Serial(PUERTO_ARDUINO_2, BAUD_RATE, timeout=1)
        time.sleep(2)
        print("Arduino 2 conectado.")
        while True:
            if ser2.in_waiting > 0:
                linea = ser2.readline().decode('utf-8').strip()
                print(f"Arduino 2: {linea}")
                # Procesa los datos aquí (por ejemplo, temperatura y gas)
                match = re.match(r"temperatura:\s*([\d.]+),\s*gas:\s*(\d+)", linea, re.IGNORECASE)
                if match:
                    temperatura = float(match.group(1))
                    gas = int(match.group(2))
                    procesar_temperatura_gas(temperatura, gas)
    except serial.SerialException as error:
        print(f"Error en Arduino 2: {error}")
    finally:
        if ser2.is_open:
            ser2.close()

# Función para procesar UID de tarjetas
def procesar_uid(linea):
    try:
        uid = linea.split(":")[1].strip().lower()
        fecha_actual = datetime.now().strftime('%Y-%m-%d')
        hora_actual = datetime.now().strftime('%H:%M:%S')
        cursor.execute("""INSERT INTO rfid_tarjetas (uid_tarjeta, estado, fecha, hora) VALUES (%s, %s, %s, %s)""",
                       (uid, "registrado", fecha_actual, hora_actual))
        db_connection.commit()
        print(f"UID registrado: {uid}")
    except mysql.connector.Error as error:
        print(f"Error al guardar UID: {error}")

# Función para procesar temperatura y gas
def procesar_temperatura_gas(temperatura, gas):
    try:
        fecha_actual = datetime.now()
        if temperatura > UMBRAL_TEMPERATURA:
            cursor.execute("""INSERT INTO temperatura (fecha, temperatura, ubicacion) VALUES (%s, %s, %s)""",
                           (fecha_actual, temperatura, "Maqueta Data Center"))
            db_connection.commit()
            print(f"Temperatura registrada: {temperatura}°C")

        if gas > UMBRAL_GAS:
            cursor.execute("""INSERT INTO sensores_humo (rango, fecha, hora) VALUES (%s, %s, %s)""",
                           (gas, fecha_actual.strftime('%Y-%m-%d'), fecha_actual.strftime('%H:%M:%S')))
            db_connection.commit()
            print(f"Gas registrado: {gas}")
    except mysql.connector.Error as error:
        print(f"Error al guardar temperatura/gas: {error}")

# Ejecutar hilos para manejar ambos Arduinos
try:
    thread_arduino_1 = threading.Thread(target=manejar_arduino_1)
    thread_arduino_2 = threading.Thread(target=manejar_arduino_2)

    thread_arduino_1.start()
    thread_arduino_2.start()

    thread_arduino_1.join()
    thread_arduino_2.join()
except KeyboardInterrupt:
    print("\nFinalizando programa.")
finally:
    if cursor:
        cursor.close()
    if db_connection:
        db_connection.close()
    print("Conexiones cerradas.")
