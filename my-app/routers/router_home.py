from controllers.funciones_login import *
from app import app
from flask import render_template, request, flash, redirect, url_for, session
import mysql.connector
from mysql.connector import Error
from controllers.funciones_home import connectionBD

# Importando conexión a BD
from controllers.funciones_home import *

@app.route('/lista-de-areas', methods=['GET'])
def lista_areas():
    if 'conectado' in session:
        return render_template('public/usuarios/lista_areas.html', areas=lista_areasBD(), dataLogin=dataLoginSesion())
    else:
        flash('Primero debes iniciar sesión.', 'error')
        return redirect(url_for('inicio'))

@app.route("/lista-de-usuarios", methods=['GET'])
def usuarios():
    if 'conectado' in session:
        return render_template('public/usuarios/lista_usuarios.html', resp_usuariosBD=lista_usuariosBD(), dataLogin=dataLoginSesion(), areas=lista_areasBD(), roles=lista_rolesBD())
    else:
        return redirect(url_for('inicioCpanel'))

# Ruta especificada para eliminar un usuario
@app.route('/borrar-usuario/<string:id>', methods=['GET'])
def borrarUsuario(id):
    resp = eliminarUsuario(id)
    if resp:
        flash('El Usuario fue eliminado correctamente', 'success')
        return redirect(url_for('usuarios'))

@app.route('/borrar-area/<string:id_area>/', methods=['GET'])
def borrarArea(id_area):
    resp = eliminarArea(id_area)
    if resp:
        flash('El Empleado fue eliminado correctamente', 'success')
        return redirect(url_for('lista_areas'))
    else:
        flash('Hay usuarios que pertenecen a esta área', 'error')
        return redirect(url_for('lista_areas'))

@app.route("/descargar-informe-accesos/", methods=['GET'])
def reporteBD():
    if 'conectado' in session:
        return generarReporteExcel()
    else:
        flash('Primero debes iniciar sesión.', 'error')
        return redirect(url_for('inicio'))

@app.route("/reporte-accesos", methods=['GET'])
def reporteAccesos():
    if 'conectado' in session:
        userData = dataLoginSesion()
        return render_template('public/perfil/reportes.html', reportes=dataReportes(), lastAccess=lastAccessBD(userData.get('cedula')), dataLogin=dataLoginSesion())

@app.route("/interfaz-clave", methods=['GET','POST'])
def claves():
    return render_template('public/usuarios/generar_clave.html', dataLogin=dataLoginSesion())

@app.route('/generar-y-guardar-clave/<string:id>', methods=['GET','POST'])
def generar_clave(id):
    print(id)
    clave_generada = crearClave()  # Llama a la función para generar la clave
    guardarClaveAuditoria(clave_generada, id)
    return clave_generada

# CREAR AREA
@app.route('/crear-area', methods=['GET','POST'])
def crearArea():
    if request.method == 'POST':
        area_name = request.form['nombre_area']  # Asumiendo que 'nombre_area' es el nombre del campo en el formulario
        resultado_insert = guardarArea(area_name)
        if resultado_insert:
            # Éxito al guardar el área
            flash('El Area fue creada correctamente', 'success')
            return redirect(url_for('lista_areas'))
        else:
            # Manejar error al guardar el área
            return "Hubo un error al guardar el área."
    return render_template('public/usuarios/lista_areas')

# ACTUALIZAR AREA
@app.route('/actualizar-area', methods=['POST'])
def updateArea():
    if request.method == 'POST':
        nombre_area = request.form['nombre_area']  # Asumiendo que 'nuevo_nombre' es el nombre del campo en el formulario
        id_area = request.form['id_area']
        resultado_update = actualizarArea(id_area, nombre_area)
        if resultado_update:
           # Éxito al actualizar el área
            flash('El área fue actualizada correctamente', 'success')
            return redirect(url_for('lista_areas'))
        else:
            # Manejar error al actualizar el área
            return "Hubo un error al actualizar el área."

    return redirect(url_for('lista_areas'))
def obtenerDatosTemperatura(page=1, per_page=15):
    try:
        # Establecer conexión a la base de datos
        connection = connectionBD()
        
        if connection.is_connected():
            cursor = connection.cursor(dictionary=True)  # Para obtener los resultados como diccionario
            
            # Calcular el OFFSET para la paginación
            offset = (page - 1) * per_page
            
            # Consulta SQL para obtener los registros de temperatura con paginación
            query = f"SELECT * FROM temperatura ORDER BY fecha DESC LIMIT {per_page} OFFSET {offset};"
            cursor.execute(query)
            
            # Obtener los resultados
            datos = cursor.fetchall()
            cursor.close()  # Cerrar cursor
            connection.close()  # Cerrar conexión
            
            return datos
    
    except mysql.connector.Error as error:
        print(f"Error al obtener los datos de temperatura: {error}")
        return []


# Modificamos la ruta para manejar la paginación
@app.route("/temperatura", methods=['GET'])
def temperatura():
    if 'conectado' in session:
        # Obtener el número de página desde la URL, por defecto es la página 1
        page = request.args.get('page', 1, type=int)
        
        # Obtener los datos de temperatura desde la base de datos con paginación
        datos_temperatura = obtenerDatosTemperatura(page=page)  # Esta función debe devolver los datos de temperatura
        
        # Obtener el total de registros para la paginación
        connection = connectionBD()
        cursor = connection.cursor(dictionary=True)
        cursor.execute("SELECT COUNT(*) AS total FROM temperatura;")
        total_registros = cursor.fetchone()['total']
        cursor.close()
        connection.close()
        
        # Calcular el número total de páginas
        per_page = 15
        total_paginas = (total_registros // per_page) + (1 if total_registros % per_page > 0 else 0)
        
        return render_template('public/temperatura.html', 
                               datos_temperatura=datos_temperatura, 
                               total_paginas=total_paginas, 
                               page=page, 
                               dataLogin=dataLoginSesion())
    else:
        flash('Primero debes iniciar sesión.', 'error')
        return redirect(url_for('inicio'))


def obtenerDatosSensoresHumo():
    try:
        # Establecer conexión a la base de datos
        connection = connectionBD()
        
        if connection.is_connected():
            cursor = connection.cursor(dictionary=True)  # Para obtener los resultados como diccionario
            # Consulta SQL para obtener los registros de sensores de humo
            query = "SELECT * FROM sensores_humo ORDER BY fecha DESC LIMIT 10;"  # Últimos 10 registros
            cursor.execute(query)
            
            # Obtener los resultados
            datos = cursor.fetchall()
            cursor.close()  # Cerrar cursor
            connection.close()  # Cerrar conexión
            
            return datos
    
    except mysql.connector.Error as error:
        print(f"Error al obtener los datos de sensores de humo: {error}")
        return []

# RUTA PARA MOSTRAR DATOS DE RFID
@app.route("/rfid", methods=['GET'])
def rfid():
    if 'conectado' in session:
        # Obtener los datos de RFID desde la base de datos
        datos_rfid = obtenerDatosRFID()  # Esta función debe devolver los datos de las tarjetas RFID
        return render_template('public/rfid.html', datos_rfid=datos_rfid, dataLogin=dataLoginSesion())
    else:
        flash('Primero debes iniciar sesión.', 'error')
        return redirect(url_for('inicio'))

# RUTA PARA MOSTRAR DATOS DE SENSORES DE HUMO
@app.route("/sensores-humo", methods=['GET'])
def sensores_humo():
    if 'conectado' in session:
        # Obtener los datos de sensores de humo desde la base de datos
        datos_sensores_humo = obtenerDatosSensoresHumo()  # Esta función debe devolver los datos de los sensores de humo
        return render_template('public/sensor_humo.html', datos_sensores_humo=datos_sensores_humo, dataLogin=dataLoginSesion())
    else:
        flash('Primero debes iniciar sesión.', 'error')
        return redirect(url_for('inicio'))

