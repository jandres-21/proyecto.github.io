# -*- coding: utf-8 -*-
from controllers.funciones_login import *  # Asegúrate de que dataLoginSesion() y otras funciones estén definidas allí
from app import app
from flask import render_template, request, flash, redirect, url_for, session, jsonify
import mysql.connector
from mysql.connector import Error
import time
import threading  # Solo se importa si se usan otras tareas; en este caso, no lo usaremos para monitorear el humo
from datetime import datetime
from flask_socketio import SocketIO, emit
from controllers.funciones_home import connectionBD, eliminarUsuario

# Inicialización de Socket.IO (con CORS permitido)
socketio = SocketIO(app, cors_allowed_origins="*")

###########################
# Funciones y rutas para TEMPERATURA
###########################

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

def monitorear_temperatura():
    temperatura_anterior = None
    while True:
        nueva_temperatura = obtenerTemperaturaActual()
        if nueva_temperatura is not None and nueva_temperatura != temperatura_anterior:
            temperatura_anterior = nueva_temperatura
            # Emitir eventos para la temperatura
            socketio.emit('temperature_update', {'temperature': nueva_temperatura})
            socketio.emit('new_temperature_record', {
                'fecha': time.strftime('%Y-%m-%d %H:%M:%S'),
                'temperatura': nueva_temperatura
            })
        time.sleep(3)  # Revisar cada 3 segundos

# Iniciar el monitoreo de temperatura en un hilo separado (puedes mantener esto si lo deseas)
threading.Thread(target=monitorear_temperatura, daemon=True).start()
@app.route("/temperatura_data", methods=["GET"])
def temperatura_data():
    datos = obtenerDatosTemperatura(page=1)  # O la consulta que desees
    return jsonify(datos)


###########################
# Rutas y funciones para USUARIOS, ÁREAS, RFID, etc.
###########################

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
                cursor.execute(querySQL)
                areasBD = cursor.fetchall()
        return areasBD
    except Exception as e:
        print(f"Error en lista_areas : {e}")
        return []

def lista_usuariosBD():
    try:
        connection = connectionBD()
        if connection.is_connected():
            cursor = connection.cursor(dictionary=True)
            cursor.execute("SELECT * FROM usuarios")
            usuarios = cursor.fetchall()
            print("Usuarios:", usuarios)
            cursor.close()
            connection.close()
            return usuarios
        else:
            print("No se pudo conectar a la base de datos.")
            return []
    except mysql.connector.Error as error:
        print(f"Error al obtener usuarios: {error}")
        return []

@app.route("/lista-de-usuarios", methods=['GET'])
def usuarios():
    if 'conectado' in session:
        usuarios_data = lista_usuariosBD()
        areas_data = lista_areasBD()
        roles_data = lista_rolesBD()

        print("Usuarios:", usuarios_data)
        print("Áreas:", areas_data)
        print("Roles:", roles_data)

        return render_template('public/usuarios/lista_usuarios.html',
                               resp_usuariosBD=usuarios_data,
                               dataLogin=dataLoginSesion(),
                               areas=areas_data,
                               roles=roles_data)
    else:
        return redirect(url_for('inicioCpanel'))

@app.route('/borrar-usuario/<string:id>', methods=['GET', 'POST'])
def borrarUsuario(id):
    if request.method == 'POST':
        resp = eliminarUsuario(id)
        
        if resp:
            if str(session.get('id')) == str(id):
                flash('Tu cuenta ha sido eliminada. Se cerrará la sesión.', 'warning')
                return redirect(url_for('cerraSesion'))
            else:
                flash('El Usuario fue eliminado correctamente', 'success')
        else:
            flash('Error al eliminar el usuario', 'error')
        
        return redirect(url_for('usuarios'))

@app.route('/lista-de-areas', methods=['GET'])
def lista_areas():
    if 'conectado' in session:
        return render_template('public/usuarios/lista_areas.html', areas=lista_areasBD(), dataLogin=dataLoginSesion())
    else:
        flash('Primero debes iniciar sesión.', 'error')
        return redirect(url_for('inicioCpanel'))

# Función para obtener datos RFID con paginación
def obtenerDatosRFID(pagina, limite=20):
    try:
        connection = connectionBD()
        if connection.is_connected():
            cursor = connection.cursor(dictionary=True)
            offset = (pagina - 1) * limite
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
                ORDER BY rfid_tarjetas.fecha DESC, rfid_tarjetas.hora DESC
                LIMIT %s OFFSET %s;
            """
            cursor.execute(query, (limite, offset))
            datos = cursor.fetchall()
            cursor.execute("SELECT COUNT(*) AS total FROM rfid_tarjetas")
            total_registros = cursor.fetchone()["total"]
            total_paginas = (total_registros // limite) + (1 if total_registros % limite > 0 else 0)
            return datos, total_paginas
    except mysql.connector.Error as error:
        print(f"Error al obtener los datos de RFID: {error}")
        return [], 0
    finally:
        if connection.is_connected():
            cursor.close()
            connection.close()

@app.route("/rfid", methods=['GET'])
def rfid():
    if 'conectado' in session:
        pagina = request.args.get('pagina', 1, type=int)
        datos_rfid, total_paginas = obtenerDatosRFID(pagina)
        return render_template('public/rfid.html', 
                               datos_rfid=datos_rfid, 
                               total_paginas=total_paginas, 
                               pagina_actual=pagina, 
                               dataLogin=dataLoginSesion())
    else:
        flash('Primero debes iniciar sesión.', 'error')
        return redirect(url_for('inicio'))

###########################
# Funciones y rutas para SENSOR DE HUMO
###########################

def obtenerNivelHumoActual():
    try:
        connection = connectionBD()
        if connection.is_connected():
            cursor = connection.cursor(dictionary=True)
            cursor.execute("SELECT rango FROM nivel_humo WHERE id = 1;")
            resultado = cursor.fetchone()
            cursor.close()
            connection.close()
            print("Resultado de obtenerNivelHumoActual:", resultado)
            return float(resultado['rango']) if resultado and resultado['rango'] is not None else 0
    except mysql.connector.Error as error:
        print(f"Error al obtener el nivel de humo: {error}")
        return 0

def obtenerDatosHumo(page=1, per_page=20):
    try:
        connection = connectionBD()
        if connection.is_connected():
            cursor = connection.cursor(dictionary=True)
            offset = (page - 1) * per_page
            query = "SELECT * FROM sensores_humo ORDER BY fecha DESC, hora DESC LIMIT %s OFFSET %s;"
            cursor.execute(query, (per_page, offset))
            datos = cursor.fetchall()
            cursor.close()
            connection.close()
            return datos
    except mysql.connector.Error as error:
        print(f"Error al obtener los datos de humo: {error}")
        return []

@app.route("/sensores-humo", methods=['GET'])
def sensores_humo():
    if 'conectado' in session:
        nivel_actual = obtenerNivelHumoActual()
        print("Nivel actual obtenido:", nivel_actual)
        page = request.args.get('page', 1, type=int)
        datos_humo = obtenerDatosHumo(page=page)
        connection = connectionBD()
        cursor = connection.cursor(dictionary=True)
        cursor.execute("SELECT COUNT(*) AS total FROM sensores_humo;")
        total_registros = cursor.fetchone()['total']
        cursor.close()
        connection.close()
        per_page = 20
        total_paginas = (total_registros // per_page) + (1 if total_registros % per_page > 0 else 0)
        return render_template('public/sensor_humo.html',
                               datos_sensores_humo=datos_humo,
                               total_paginas=total_paginas,
                               pagina=page,
                               nivel_actual=nivel_actual,
                               dataLogin=dataLoginSesion())
    else:
        flash('Primero debes iniciar sesión.', 'error')
        return redirect(url_for('inicio'))

@socketio.on('connect')
def handle_connect():
    print("Cliente conectado al sensor de humo")

def monitorear_humo():
    while True:
        nuevo_nivel = obtenerNivelHumoActual()
        print("Nuevo nivel de humo:", nuevo_nivel)
        socketio.emit('update_nivel_humo', {'nivel': float(nuevo_nivel)})
        socketio.emit('new_humo_record', {
            'fecha': time.strftime('%Y-%m-%d'),
            'hora': time.strftime('%H:%M:%S'),
            'rango': float(nuevo_nivel)
        })
        time.sleep(3)

@app.route("/sensores-humo-data", methods=["GET"])
def sensores_humo_data():
    # Puedes usar la función obtenerDatosHumo y, si lo deseas, filtrar el último valor.
    datos = obtenerDatosHumo(page=1, per_page=20)
    # Si deseas excluir el registro más reciente (por ejemplo, el primero en la lista),
    # puedes hacer: datos = datos[1:]
    return jsonify(datos)


# Iniciar el monitoreo del sensor de humo en segundo plano (solo una de las siguientes líneas)
socketio.start_background_task(monitorear_humo)
# threading.Thread(target=monitorear_humo, daemon=True).start()  <-- Esta línea se ha comentado

###########################
# Rutas y funciones para TARJETAS y CONSUMO ELÉCTRICO
###########################

def ObtenerTargeta():
    try:
        connection = connectionBD()
        if connection.is_connected():
            cursor = connection.cursor(dictionary=True)
            cursor.execute("SELECT codigo FROM Targeta")
            usuarios = cursor.fetchall()
            if usuarios:
                ultimo_codigo = usuarios[-1]['codigo']
                cursor.close()
                connection.close()
                return ultimo_codigo
            else:
                cursor.close()
                connection.close()
                return None
    except mysql.connector.Error as error:
        print(f"Error al obtener código de tarjeta: {error}")
        return None

@app.route('/obtener_targeta', methods=['GET'])
def obtener_targeta():
    ultimo_codigo = ObtenerTargeta()
    if ultimo_codigo:
        return jsonify({'codigo': ultimo_codigo})
    else:
        return jsonify({'error': 'No se encontró ningún código de tarjeta.'}), 404

def obtenerDatosElectricos(page=1, per_page=15):
    try:
        connection = connectionBD()
        if connection.is_connected():
            cursor = connection.cursor(dictionary=True)
            offset = (page - 1) * per_page
            cursor.execute(f"SELECT * FROM datos_electricos ORDER BY fecha DESC, hora DESC LIMIT {per_page} OFFSET {offset};")
            datos = cursor.fetchall()
            cursor.close()
            connection.close()
            return datos
    except mysql.connector.Error as error:
        print(f"Error al obtener los datos eléctricos: {error}")
        return []

@app.route("/consumo_electrico", methods=['GET'])
def consumo_electrico():
    if 'conectado' in session:
        page = request.args.get('page', 1, type=int)
        datos = obtenerDatosElectricos(page=page)
        connection = connectionBD()
        cursor = connection.cursor(dictionary=True)
        cursor.execute("SELECT COUNT(*) AS total FROM datos_electricos;")
        total_registros = cursor.fetchone()['total']
        cursor.close()
        connection.close()
        per_page = 15
        total_paginas = (total_registros // per_page) + (1 if total_registros % per_page > 0 else 0)
        dataLogin = dataLoginSesion()
        return render_template('public/consumo_electrico.html',
                               datos_electricos=datos,
                               total_paginas=total_paginas,
                               page=page,
                               dataLogin=dataLogin)
    else:
        flash('Primero debes iniciar sesión.', 'error')
        return redirect(url_for('inicio'))

@app.route("/api/consumo_actual", methods=['GET'])
def obtener_consumo_actual():
    try:
        connection = connectionBD()
        cursor = connection.cursor(dictionary=True)
        cursor.execute("SELECT voltaje, corriente FROM consumo_actual WHERE id = 1;")
        consumo = cursor.fetchone() or {"voltaje": 0, "corriente": 0}
        return jsonify(consumo)
    except mysql.connector.Error as error:
        print(f"Error al obtener consumo actual: {error}")
        return jsonify({"voltaje": 0, "corriente": 0})
    finally:
        if cursor:
            cursor.close()
        if connection:
            connection.close()

###########################
# Arranque de la aplicación
###########################

if __name__ == "__main__":
    socketio.run(app, debug=True)
