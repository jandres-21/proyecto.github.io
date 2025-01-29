from controllers.funciones_login import *
from app import app
from flask import render_template, request, flash, redirect, url_for, session
from flask_socketio import SocketIO
import mysql.connector
from controllers.funciones_home import connectionBD

# Configurar Socket.IO
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
import time
import threading

def monitorear_temperatura():
    temperatura_anterior = None
    while True:
        nueva_temperatura = obtenerTemperaturaActual()
        if nueva_temperatura is not None and nueva_temperatura != temperatura_anterior:
            temperatura_anterior = nueva_temperatura
            socketio.emit('temperature_update', {'temperature': nueva_temperatura})
        time.sleep(3)  # Se revisa cada 3 segundos

# Iniciar el monitoreo en un hilo separado
threading.Thread(target=monitorear_temperatura, daemon=True).start()

# Ejecutar el servidor con WebSockets
if __name__ == '__main__':
    socketio.run(app, debug=True)
