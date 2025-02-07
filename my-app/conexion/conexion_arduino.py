import serial
import mysql.connector
import time
from datetime import datetime
import re
from datetime import datetime, timedelta

# Configuración de umbrales
umbral_temperatura = 25.0
umbral_gas = 500
acum_voltaje = 0.0       # Suma de los voltajes medidos
acum_corriente = 0.0     # Suma de las corrientes medidas
acum_consumo = 0.0       # Suma de la energía en kWh calculada
count_readings = 0       # Número de mediciones acumuladas
ultimo_registro_hora = None  # Fecha y hora del inicio del acumulado

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
        # Actualizar siempre el valor en la tabla `nivel_humo`
        cursor.execute("""
            INSERT INTO nivel_humo (id, rango)
            VALUES (1, %s)
            ON DUPLICATE KEY UPDATE rango = %s
        """, (rango, rango))
        db_connection.commit()
        print(f"Actualizado en 'nivel_humo': Rango: {rango}")

        # Verificar si el rango supera el umbral y es un múltiplo de 500 superior al último registrado
        if rango > umbral_gas and (rango // 500) * 500 > ultimo_rango_guardado:
            # Obtener la fecha y hora actuales
            fecha_actual = datetime.now().strftime('%Y-%m-%d')  # Solo la fecha (YYYY-MM-DD)
            hora_actual = datetime.now().strftime('%H:%M:%S')  # Solo la hora (HH:MM:SS)

            # Guardar en la tabla `sensores_humo`
            cursor.execute("""
                INSERT INTO sensores_humo (rango, fecha, hora)
                VALUES (%s, %s, %s)
            """, (rango, fecha_actual, hora_actual))
            db_connection.commit()
            print(f"Gas guardado en 'sensores_humo': {fecha_actual} {hora_actual}, Rango: {rango}")

            # Actualizar el último rango guardado con el múltiplo de 500 más cercano
            ultimo_rango_guardado = (rango // 500) * 500
        else:
            print(f"El valor de rango ({rango}) no cumple las condiciones para guardarse en 'sensores_humo'.")
    
    except mysql.connector.Error as error:
        # Manejo de errores
        print(f"Error al guardar datos de gas: {error}")


# Función para guardar datos de voltaje y corriente

def guardar_datos_electricos(voltaje, corriente, cursor, connection):
    global acum_voltaje, acum_corriente, acum_consumo, count_readings, ultimo_registro_hora
    try:
        # Obtener la fecha y hora actuales
        ahora = datetime.now()
        fecha_actual = ahora.strftime('%Y-%m-%d')
        hora_actual = ahora.strftime('%H:%M:%S')
        
        # Inicializar el acumulador si es la primera medición
        if ultimo_registro_hora is None:
            ultimo_registro_hora = ahora
        
        # Actualizar la tabla "consumo_actual" con los datos en tiempo real (1 solo registro)
        cursor.execute("""
            INSERT INTO consumo_actual (id, voltaje, corriente) 
            VALUES (1, %s, %s)
            ON DUPLICATE KEY UPDATE voltaje = %s, corriente = %s;
        """, (voltaje, corriente, voltaje, corriente))
        
        # --- Acumular mediciones ---
        # Actualizar acumuladores con la medición actual
        acum_voltaje += voltaje
        acum_corriente += corriente
        count_readings += 1
        
        # Calcular la energía consumida en este intervalo (3 segundos) en kWh
        # Intervalo en horas: 3 segundos = 3/3600 horas
        intervalo_horas = 3 / 3600  
        energia = (voltaje * corriente) / 1000 * intervalo_horas  # (W/1000 = kW) * horas = kWh
        acum_consumo += energia
        
        # --- Verificar si ha pasado 1 hora desde el último registro agregado en "datos_electricos" ---
        if ahora - ultimo_registro_hora >= timedelta(hours=1):
            # Calcular promedios
            promedio_voltaje = acum_voltaje / count_readings
            promedio_corriente = acum_corriente / count_readings
            consumo_total_kwh = acum_consumo  # Acumulado en kWh durante la hora

            # Insertar nuevo registro en "datos_electricos" con los datos agregados de la hora
            # Se asume que la tabla datos_electricos tiene una columna "consumo_kwh"
            cursor.execute("""
                INSERT INTO datos_electricos (voltaje, corriente, fecha, hora, consumo_kwh)
                VALUES (%s, %s, %s, %s, %s);
            """, (promedio_voltaje, promedio_corriente, fecha_actual, hora_actual, consumo_total_kwh))
            print(f"✅ Registro horario guardado: Promedio Voltaje: {promedio_voltaje:.2f} V, Promedio Corriente: {promedio_corriente:.2f} A, Consumo: {consumo_total_kwh:.3f} kWh - {fecha_actual} {hora_actual}")
            
            # Reiniciar acumuladores para la siguiente hora
            acum_voltaje = 0.0
            acum_corriente = 0.0
            acum_consumo = 0.0
            count_readings = 0
            ultimo_registro_hora = ahora

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
        
        query = """
            INSERT INTO rfid_tarjetas (uid_tarjeta, estado, fecha, hora, cedula)
            VALUES (%s, %s, %s, %s, %s)
        """
        cursor.execute(query, (uid, estado_acceso, fecha_actual, hora_actual, cedula_usuario))
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
                # Consultar en la base de datos, seleccionando explícitamente la columna "cedula"
                cursor.execute("SELECT cedula FROM usuarios WHERE LOWER(tarjeta) = %s", (uid,))
                result = cursor.fetchone()
                estado_acceso = "permitido" if result else "denegado"
                # Se obtiene la cédula en la posición 0, ya que la consulta trae solo esa columna
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
                    # Esperar 10 segundos antes de eliminar el registro
                    time.sleep(10)
                    # Eliminar el registro (TRUNCATE vacía la tabla)
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

                    guardar_datos_gas(gas)  #guardar datos gas

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
