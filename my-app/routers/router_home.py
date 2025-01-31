from controllers.funciones_login import *
from app import app
from flask import render_template, request, flash, redirect, url_for, session
import mysql.connector
from flask_socketio import SocketIO
from mysql.connector import Error
from controllers.funciones_home import connectionBD
import time
import threading
from controllers.funciones_home import eliminarUsuario
from flask import request, jsonify

socketio = SocketIO(app, cors_allowed_origins="*")

# Función para obtener la temperatura actual
def obtenerTemperaturaActual():
    try:
        connection = connectionBD()
        if connection.is_connected():
            cursor = connection.cursor(dictionary=True)
            cursor.execute("SELECT temperatura FROM temperatura_actual ORDER BY fecha DESC LIMIT 1;")
            resultado = cursor.fetchone()
            cursor.close()
            connection.close()
            return resultado['temperatura'] if resultado else None
    except mysql.connector.Error as error:
        print(f"Error al obtener la temperatura actual: {error}")
        return None

# Función para obtener datos de temperatura con paginación
def obtenerDatosTemperatura(page=1, per_page=15):
    try:
        connection = connectionBD()
        if connection.is_connected():
            cursor = connection.cursor(dictionary=True)
            offset = (page - 1) * per_page
            cursor.execute(f"SELECT * FROM temperatura ORDER BY fecha DESC LIMIT {per_page} OFFSET {offset};")
            datos = cursor.fetchall()
            cursor.close()
            connection.close()
            return datos
    except mysql.connector.Error as error:
        print(f"Error al obtener los datos de temperatura: {error}")
        return []

# Ruta para mostrar los datos de temperatura
@app.route("/temperatura", methods=['GET'])
def temperatura():
    if 'conectado' in session:
        temperatura_actual = obtenerTemperaturaActual()
        page = request.args.get('page', 1, type=int)
        datos_temperatura = obtenerDatosTemperatura(page=page)

        # Obtener total de registros para paginación
        connection = connectionBD()
        cursor = connection.cursor(dictionary=True)
        cursor.execute("SELECT COUNT(*) AS total FROM temperatura;")
        total_registros = cursor.fetchone()['total']
        cursor.close()
        connection.close()

        per_page = 15
        total_paginas = (total_registros // per_page) + (1 if total_registros % per_page > 0 else 0)

        return render_template('public/temperatura.html',
                               datos_temperatura=datos_temperatura,
                               total_paginas=total_paginas,
                               page=page,
                               temperatura_actual=temperatura_actual,
                               dataLogin=dataLoginSesion())
    else:
        flash('Primero debes iniciar sesión.', 'error')
        return redirect(url_for('inicio'))

# Función para monitorear la temperatura y enviar actualizaciones en tiempo real
def monitorear_temperatura():
    temperatura_anterior = None
    while True:
        nueva_temperatura = obtenerTemperaturaActual()
        if nueva_temperatura is not None and nueva_temperatura != temperatura_anterior:
            temperatura_anterior = nueva_temperatura
            # Emitir eventos de actualización de temperatura y nuevo registro
            socketio.emit('temperature_update', {'temperature': nueva_temperatura})
            socketio.emit('new_temperature_record', {
                'fecha': time.strftime('%Y-%m-%d %H:%M:%S'),
                'temperatura': nueva_temperatura
            })
        time.sleep(3)  # Revisa cada 3 segundos

# Iniciar el monitoreo en un hilo separado
threading.Thread(target=monitorear_temperatura, daemon=True).start()

# Ruta para listar áreas
@app.route('/lista-de-areas', methods=['GET'])
def lista_areas():
    if 'conectado' in session:
        return render_template('public/usuarios/lista_areas.html', areas=lista_areasBD(), dataLogin=dataLoginSesion())
    else:
        flash('Primero debes iniciar sesión.', 'error')
        return redirect(url_for('inicioCpanel'))

def lista_rolesBD():
    try:
        with connectionBD() as conexion_MYSQLdb:
            with conexion_MYSQLdb.cursor(dictionary=True) as cursor:
                querySQL = "SELECT * FROM rol"
                cursor.execute(querySQL)
                roles = cursor.fetchall()
                return roles
    except Exception as e:
        print(f"Error en select roles : {e}")
        return []
    
def lista_areasBD():
    try:
        with connectionBD() as conexion_MySQLdb:
            with conexion_MySQLdb.cursor(dictionary=True) as cursor:
                querySQL = "SELECT id_area, nombre_area FROM area"
                cursor.execute(querySQL,)
                areasBD = cursor.fetchall()
        return areasBD
    except Exception as e:
        print(f"Error en lista_areas : {e}")
        return []
 


# Función corregida de lista de usuarios con verificación de base de datos
def lista_usuariosBD():
    try:
        connection = connectionBD()
        if connection.is_connected():
            cursor = connection.cursor(dictionary=True)
            cursor.execute("SELECT * FROM usuarios")  # Asegúrate de que la consulta sea correcta
            usuarios = cursor.fetchall()
            print("Usuarios:", usuarios)  # Verifica los datos obtenidos
            cursor.close()
            connection.close()
            return usuarios
        else:
            print("No se pudo conectar a la base de datos.")
            return []
    except mysql.connector.Error as error:
        print(f"Error al obtener usuarios: {error}")
        return []

# Ruta para listar usuarios
@app.route("/lista-de-usuarios", methods=['GET'])
def usuarios():
    if 'conectado' in session:
        usuarios_data = lista_usuariosBD()
        areas_data = lista_areasBD()
        roles_data = lista_rolesBD()

        print("Usuarios:", usuarios_data)  # Verifica los datos de usuarios
        print("Áreas:", areas_data)  # Verifica los datos de áreas
        print("Roles:", roles_data)  # Verifica los datos de roles

        return render_template('public/usuarios/lista_usuarios.html',
                               resp_usuariosBD=usuarios_data,
                               dataLogin=dataLoginSesion(),
                               areas=areas_data,
                               roles=roles_data)
    else:
        return redirect(url_for('inicioCpanel'))

# Ruta para eliminar un usuario
@app.route('/borrar-usuario/<string:id>', methods=['GET', 'POST'])
def borrarUsuario(id):
    if request.method == 'POST':
        # Llamar a la función para eliminar el usuario
        resp = eliminarUsuario(id)
        
        if resp:
            flash('El Usuario fue eliminado correctamente', 'success')
        else:
            flash('Error al eliminar el usuario', 'error')
        
        return redirect(url_for('usuarios'))

def obtenerDatosRFID():
    try:
        # Establecer conexión a la base de datos
        connection = connectionBD()  # Aquí debes tener definida tu función de conexión
        
        if connection.is_connected():
            cursor = connection.cursor(dictionary=True)  # Para obtener los resultados como diccionario
            
            # Consulta SQL para obtener los registros de tarjetas RFID con datos del usuario
            query = """
                SELECT 
    rfid_tarjetas.id, 
    rfid_tarjetas.uid_tarjeta, 
    rfid_tarjetas.estado, 
    rfid_tarjetas.cedula, 
    rfid_tarjetas.fecha, 
    rfid_tarjetas.hora, 
    usuarios.nombre_usuario AS nombre, 
    usuarios.apellido_usuario AS apellido
FROM rfid_tarjetas
LEFT JOIN usuarios ON rfid_tarjetas.cedula = usuarios.cedula
ORDER BY rfid_tarjetas.fecha DESC
LIMIT 10;

            """
            cursor.execute(query)
            
            # Obtener los resultados
            datos = cursor.fetchall()
            return datos
    
    except mysql.connector.Error as error:
        print(f"Error al obtener los datos de RFID: {error}")
        return []
    
    finally:
        if connection.is_connected():
            cursor.close()  # Cerrar cursor
            connection.close()  # Cerrar conexión



@app.route("/rfid", methods=['GET'])
def rfid():
    if 'conectado' in session:
        # Obtener los datos de RFID desde la base de datos
        datos_rfid = obtenerDatosRFID()  # Esta función debe devolver los datos de las tarjetas RFID
        return render_template('public/rfid.html', datos_rfid=datos_rfid, dataLogin=dataLoginSesion())
    else:
        flash('Primero debes iniciar sesión.', 'error')
        return redirect(url_for('inicio'))



def obtenerDatosSensoresHumo(page=1, per_page=10):
    try:
        connection = connectionBD()
        if connection.is_connected():
            cursor = connection.cursor(dictionary=True)

            # Obtener total de registros
            cursor.execute("SELECT COUNT(*) AS total FROM sensores_humo;")
            total_registros = cursor.fetchone()['total']

            # Calcular el offset para la paginación
            offset = (page - 1) * per_page

            # Consulta SQL con paginación
            query = "SELECT * FROM sensores_humo ORDER BY fecha DESC LIMIT %s OFFSET %s;"
            cursor.execute(query, (per_page, offset))

            # Obtener los resultados
            datos = cursor.fetchall()

            # Obtener el último registro
            ultimo_registro = datos[0] if datos else None
            cursor.close()
            connection.close()

            # Comprobar si el último registro tiene un valor mayor a 100
            supera_100 = False
            if ultimo_registro and float(ultimo_registro['rango']) > 100:
                supera_100 = True

            return datos, supera_100, total_registros
    
    except mysql.connector.Error as error:
        print(f"Error al obtener los datos de sensores de humo: {error}")
        return [], False, 0
@app.route("/sensores-humo", methods=['GET'])
def sensores_humo():
    if 'conectado' in session:
        # Obtener la página actual desde la URL
        page = request.args.get('page', 1, type=int)
        per_page = 10

        # Obtener datos paginados
        datos_sensores_humo, supera_100, total_registros = obtenerDatosSensoresHumo(page, per_page)

        # Calcular total de páginas correctamente
        total_paginas = (total_registros // per_page) + (1 if total_registros % per_page > 0 else 0)

        return render_template('public/sensor_humo.html', 
                               datos_sensores_humo=datos_sensores_humo, 
                               supera_100=supera_100,
                               total_paginas=total_paginas, 
                               pagina=page, 
                               dataLogin=dataLoginSesion())
    else:
        flash('Primero debes iniciar sesión.', 'error')
        return redirect(url_for('inicio'))
    
