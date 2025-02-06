import serial
import mysql.connector
import time
from datetime import datetime
import re
from datetime import datetime, timedelta

# Configuración de umbrales
umbral_temperatura = 25.0
umbral_gas = 500

# Banderas para evitar múltiples registros
temp_superado = False
gas_superado = False

# Función para conectar a la base de datos
def connectionBD():
    print("Intentando conectar a la base de datos...")
    try:
        connection = mysql.connector.connect(
            host="34.57.72.162",      # Host de la base de datos
            port=3306,                # Puerto
            user="root",              # Usuario
            passwd="HfvkMwoYEeFwlmqQJbRZAXnyaXciAojX",  # Contraseña
            database="railway",       # Base de datos
            charset='utf8mb4',        # Codificación de caracteres
            collation='utf8mb4_unicode_ci',  # Colación
            raise_on_warnings=True    # Levanta errores si los hay
        )
        if connection.is_connected():
            print("Conexión exitosa a la BD")
            return connection
    except mysql.connector.Error as error:
        print(f"No se pudo conectar: {error}")
        return None

# Inicializar variable global
ultimo_temperatura_guardada = None  

def guardar_temperatura(temperatura):
    global ultimo_temperatura_guardada

    try:
        # Obtener la fecha y hora actuales
        fecha_actual = datetime.now()

        # Primero, actualizar la tabla 'temperatura_actual' sin importar el valor de la temperatura
        cursor.execute("""
            INSERT INTO temperatura_actual (id, temperatura, fecha)
            VALUES (1, %s, %s)
            ON DUPLICATE KEY UPDATE temperatura = %s, fecha = %s
        """, (temperatura, fecha_actual, temperatura, fecha_actual))
        db_connection.commit()
        print(f"Actualizado 'temperatura_actual': {temperatura}°C - {fecha_actual}")

        # Si la temperatura es mayor a 25 y hay un aumento de al menos 2°C
        if temperatura > 25 and (ultimo_temperatura_guardada is None or temperatura >= ultimo_temperatura_guardada + 2):
            # Insertar en la tabla 'temperatura'
            cursor.execute("""
                INSERT INTO temperatura (temperatura, fecha)
                VALUES (%s, %s)
            """, (temperatura, fecha_actual))
            db_connection.commit()
            print(f"Temperatura registrada en 'temperatura': {temperatura}°C - {fecha_actual}")

            # Actualizar el último valor guardado
            ultimo_temperatura_guardada = temperatura
        else:
            # Solo actualizamos 'temperatura_actual' sin insertar en la tabla 'temperatura'
            print(f"No se guarda en 'temperatura' ya que la temperatura es {temperatura}°C y no cumple las condiciones.")
            
    except mysql.connector.Error as error:
        print(f"Error al guardar temperatura: {error}")

# Variable global para almacenar el último múltiplo de 500 guardado
ultimo_rango_guardado = 0

def guardar_datos_gas(rango, umbral_gas):
    global ultimo_rango_guardado  # Usamos la variable global

    try:
        # Verificar si el rango supera el umbral y si es un múltiplo de 500 superior al último registrado
        if rango > umbral_gas and (rango // 500) * 500 > ultimo_rango_guardado:
            # Obtener la fecha y hora actuales
            fecha_actual = datetime.now().strftime('%Y-%m-%d')  # Solo la fecha (YYYY-MM-DD)
            hora_actual = datetime.now().strftime('%H:%M:%S')  # Solo la hora (HH:MM:SS)
            
            # Ejecutar la consulta SQL para insertar los datos
            cursor.execute(""" 
                INSERT INTO sensores_humo (rango, fecha, hora)
                VALUES (%s, %s, %s)
            """, (rango, fecha_actual, hora_actual))
            
            # Confirmar la transacción
            db_connection.commit()
            
            # Imprimir mensaje de éxito
            print(f"Gas guardado: {fecha_actual} {hora_actual}, Rango: {rango}")

            # Actualizar el último rango guardado con el múltiplo de 500 más cercano
            ultimo_rango_guardado = (rango // 500) * 500
        else:
            print(f"El valor de rango ({rango}) no supera el umbral ({umbral_gas}) o ya se ha registrado un rango mayor o igual a ese.")
    
    except mysql.connector.Error as error:
        # Manejo de errores
        print(f"Error al guardar datos de gas: {error}")

# Función para guardar datos de voltaje y corriente

def guardar_datos_electricos(voltaje, corriente, cursor, connection):
    try:
        # Obtener la fecha y hora actuales
        fecha_actual = datetime.now().strftime('%Y-%m-%d')
        hora_actual = datetime.now().strftime('%H:%M:%S')

        # 🔹 Actualizar la tabla "consumo_actual" con los datos en tiempo real (1 solo registro)
        cursor.execute("""
            INSERT INTO consumo_actual (id, voltaje, corriente) 
            VALUES (1, %s, %s)
            ON DUPLICATE KEY UPDATE voltaje = %s, corriente = %s;
        """, (voltaje, corriente, voltaje, corriente))

        # 🔹 Verificar si ha pasado una hora desde el último registro en "datos_electricos"
        cursor.execute("SELECT fecha, hora FROM datos_electricos ORDER BY fecha DESC, hora DESC LIMIT 1;")
        ultima_medicion = cursor.fetchone()

        if ultima_medicion:
            ultima_fecha, ultima_hora = ultima_medicion
            ultima_medicion_dt = datetime.strptime(f"{ultima_fecha} {ultima_hora}", "%Y-%m-%d %H:%M:%S")
        else:
            ultima_medicion_dt = None

        ahora = datetime.now()

        if not ultima_medicion_dt or (ahora - ultima_medicion_dt >= timedelta(hours=1)):
            # Insertar nuevo registro cada hora en "datos_electricos"
            cursor.execute("""
                INSERT INTO datos_electricos (voltaje, corriente, fecha, hora)
                VALUES (%s, %s, %s, %s);
            """, (voltaje, corriente, fecha_actual, hora_actual))
            print(f"✅ Registro horario guardado en datos_electricos: {voltaje} V, {corriente} A - {fecha_actual} {hora_actual}")

        # Confirmar la transacción
        connection.commit()

    except mysql.connector.Error as error:
        print(f"❌ Error al guardar datos eléctricos: {error}")

# Configuración de conexiones
db_connection = connectionBD()
cursor = db_connection.cursor() if db_connection else None

# Configuración de los puertos seriales
try:


# Usa los nombres de los dispositivos dentro del contenedor
    ser_rfid = serial.Serial('COM3', 9600, timeout=1)  # Puerto para el Arduino RFID
    ser_sensor = serial.Serial('COM4', 9600, timeout=1)  # Puerto para el Arduino de sensores


    time.sleep(2)
    print("Conexión serie establecida.")
except serial.SerialException as error:
    print(f"Error al conectar con los puertos seriales: {error}")
    ser_rfid = ser_sensor = None

def guardar_datos_rfid(uid, estado_acceso, cedula_usuario):
    try:
        fecha_actual = datetime.now().strftime('%Y-%m-%d')
        hora_actual = datetime.now().strftime('%H:%M:%S')
        cursor.execute(""" 
            INSERT INTO rfid_tarjetas (uid_tarjeta, estado, fecha, hora, cedula)
            VALUES (%s, %s, %s, %s, %s)
        """, (uid, estado_acceso, fecha_actual, hora_actual, cedula_usuario))
        db_connection.commit()
        print(f"Acceso guardado: {uid}, Estado: {estado_acceso}")
    except mysql.connector.Error as error:
        print(f"Error al guardar datos RFID: {error}")

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
                # CORRECCIÓN: Se asume que la cedula es la primera columna del resultado
                cedula_usuario = result[0] if result else None
                guardar_datos_rfid(uid, estado_acceso, cedula_usuario)
                if result:
                    ser_rfid.write(b'1')
                else:
                    ser_rfid.write(b'0')
                if estado_acceso == "denegado":
                    # Insertar el registro en la tabla "Targeta"
                    cursor.execute(""" 
                        INSERT INTO Targeta (codigo)
                        VALUES (%s)
                    """, (uid,))
                    db_connection.commit()
                    print(f"Registro guardado en 'Targeta' con código: {uid}")
                    # Esperar 5 segundos antes de eliminar el registro
                    time.sleep(10)
                    # Eliminar el registro después de 3 segundos
                    cursor.execute("TRUNCATE TABLE Targeta")
                    db_connection.commit()
                    print(f"Registro con código {uid} eliminado después de 3 segundos.")
        if ser_sensor.in_waiting > 0:
            linea_sensor = ser_sensor.readline().decode('utf-8').strip()
            print(f"Datos de sensores recibidos: {linea_sensor}")

            # Validar formato con expresión regular
            match = re.match(
                r"Temperatura:\s*([\d.]+)\s*C,\s*Gas:\s*(\d+)\s*Voltaje:\s*([\d.]+)\s*V\s*Corriente:\s*([\d.]+)\s*A",
                linea_sensor,
                re.IGNORECASE
            )
            if match:
                try:
                    temperatura = float(match.group(1))
                    gas = int(match.group(2))
                    voltaje = float(match.group(3))
                    corriente = float(match.group(4))

                    # Guardar la temperatura en la tabla adecuada
                    guardar_temperatura(temperatura)

                    # Solo guardar el primer registro cuando el gas supera el umbral
                    if gas > umbral_gas:
                        if not gas_superado:  # Solo registrar si no se ha registrado antes
                            guardar_datos_gas(gas, umbral_gas)
                            gas_superado = True
                    else:
                        gas_superado = False  # Reinicia la bandera si vuelve a valores normales

                    # Guardar los datos de voltaje y corriente
                    guardar_datos_electricos(voltaje, corriente, cursor, db_connection)

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
