import serial
import mysql.connector
import time
from datetime import datetime
import re
from flask import Flask, render_template
from flask_socketio import SocketIO

# Configuración de Flask y WebSockets
app = Flask(__name__)
socketio = SocketIO(app)

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
            host="34.57.72.162",
            port=3306,
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

# Configuración de conexiones
db_connection = connectionBD()
cursor = db_connection.cursor() if db_connection else None

# Configuración de los puertos seriales
try:
    ser_sensor = serial.Serial('COM3', 9600, timeout=1)  # Puerto para el Arduino de sensores
    time.sleep(2)
    print("Conexión serie establecida.")
except serial.SerialException as error:
    print(f"Error al conectar con los puertos seriales: {error}")
    ser_sensor = None

# Ruta para la página principal
@app.route('/')
def index():
    return render_template('temperatura_real.html')  # Cambia el nombre del archivo si es necesario

# Leer datos de sensores en tiempo real y enviarlos al frontend
def read_serial_data():
    global temp_superado, gas_superado
    while ser_sensor and ser_sensor.is_open:
        if ser_sensor.in_waiting > 0:
            linea_sensor = ser_sensor.readline().decode('utf-8').strip()
            print(f"Datos de sensores recibidos: {linea_sensor}")

            # Validar formato con expresión regular
            match = re.match(r"temperatura:\s*([\d.]+),\s*gas:\s*(\d+)", linea_sensor, re.IGNORECASE)
            if match:
                try:
                    temperatura = float(match.group(1))
                    gas = int(match.group(2))

                    # Enviar datos al sistema web en tiempo real
                    socketio.emit('temperature_update', {'temperature': temperatura, 'gas': gas})

                    # Solo guardar el primer registro cuando la temperatura supera el umbral
                    if temperatura > UMBRAL_TEMPERATURA:
                        if not temp_superado:
                            guardar_datos_temperatura(temperatura)
                            temp_superado = True
                    else:
                        temp_superado = False

                    # Solo guardar el primer registro cuando el gas supera el umbral
                    if gas > UMBRAL_GAS:
                        if not gas_superado:
                            guardar_datos_gas(gas)
                            gas_superado = True
                    else:
                        gas_superado = False

                except ValueError as e:
                    print(f"Error al convertir valores: {e}")
            else:
                print("Formato de datos no válido.")
        time.sleep(1)

# Iniciar el servidor Flask y el proceso de lectura de datos
if __name__ == '__main__':
    if ser_sensor:
        socketio.start_background_task(target=read_serial_data)
    socketio.run(app, host='0.0.0.0', port=5000)
