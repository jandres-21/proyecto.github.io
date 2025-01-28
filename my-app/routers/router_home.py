from controllers.funciones_login import *
from app import app
from flask import render_template, request, flash, redirect, url_for, session
import mysql.connector
from mysql.connector import Error
from controllers.funciones_home import connectionBD

# Importando conexión a BD
from controllers.funciones_home import *

# Función para obtener la temperatura actual
def obtenerTemperaturaActual():
    try:
        # Establecer conexión a la base de datos
        connection = connectionBD()
        
        if connection.is_connected():
            cursor = connection.cursor(dictionary=True)  # Para obtener los resultados como diccionario
            
            # Consulta SQL para obtener el último registro de temperatura actual
            query = "SELECT temperatura FROM temperatura_actual ORDER BY fecha DESC LIMIT 1;"
            cursor.execute(query)
            
            # Obtener el resultado
            resultado = cursor.fetchone()  # Retorna un solo registro
            cursor.close()  # Cerrar cursor
            connection.close()  # Cerrar conexión
            
            # Retornar la temperatura si existe, sino retornar None
            return resultado['temperatura'] if resultado else None
    
    except mysql.connector.Error as error:
        print(f"Error al obtener la temperatura actual: {error}")
        return None

# Función para obtener datos de temperatura (paginado)
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

# Ruta para mostrar los datos de temperatura
@app.route("/temperatura", methods=['GET'])
def temperatura():
    if 'conectado' in session:
        # Obtener el valor de la temperatura actual
        temperatura_actual = obtenerTemperaturaActual()

        # Obtener los datos de temperatura desde la base de datos con paginación
        page = request.args.get('page', 1, type=int)
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
                               temperatura_actual=temperatura_actual,  # Pasamos la temperatura actual a la plantilla
                               dataLogin=dataLoginSesion())
    else:
        flash('Primero debes iniciar sesión.', 'error')
        return redirect(url_for('inicio'))

# Ruta para listar áreas
@app.route('/lista-de-areas', methods=['GET'])
def lista_areas():
    if 'conectado' in session:
        return render_template('public/usuarios/lista_areas.html', areas=lista_areasBD(), dataLogin=dataLoginSesion())
    else:
        flash('Primero debes iniciar sesión.', 'error')
        return redirect(url_for('inicio'))

# Ruta para listar usuarios
@app.route("/lista-de-usuarios", methods=['GET'])
def usuarios():
    if 'conectado' in session:
        return render_template('public/usuarios/lista_usuarios.html', resp_usuariosBD=lista_usuariosBD(), dataLogin=dataLoginSesion(), areas=lista_areasBD(), roles=lista_rolesBD())
    else:
        return redirect(url_for('inicioCpanel'))

# Ruta para eliminar un usuario
@app.route('/borrar-usuario/<string:id>', methods=['GET'])
def borrarUsuario(id):
    resp = eliminarUsuario(id)
    if resp:
        flash('El Usuario fue eliminado correctamente', 'success')
        return redirect(url_for('usuarios'))

# Ruta para eliminar un área
@app.route('/borrar-area/<string:id_area>/', methods=['GET'])
def borrarArea(id_area):
    resp = eliminarArea(id_area)
    if resp:
        flash('El Empleado fue eliminado correctamente', 'success')
        return redirect(url_for('lista_areas'))
    else:
        flash('Hay usuarios que pertenecen a esta área', 'error')
        return redirect(url_for('lista_areas'))

# Ruta para generar un reporte de accesos
@app.route("/descargar-informe-accesos/", methods=['GET'])
def reporteBD():
    if 'conectado' in session:
        return generarReporteExcel()
    else:
        flash('Primero debes iniciar sesión.', 'error')
        return redirect(url_for('inicio'))

# Ruta para reporte de accesos
@app.route("/reporte-accesos", methods=['GET'])
def reporteAccesos():
    if 'conectado' in session:
        userData = dataLoginSesion()
        return render_template('public/perfil/reportes.html', reportes=dataReportes(), lastAccess=lastAccessBD(userData.get('cedula')), dataLogin=dataLoginSesion())

# Ruta para generar una clave
@app.route("/interfaz-clave", methods=['GET','POST'])
def claves():
    return render_template('public/usuarios/generar_clave.html', dataLogin=dataLoginSesion())

# Ruta para guardar una nueva clave
@app.route('/generar-y-guardar-clave/<string:id>', methods=['GET','POST'])
def generar_clave(id):
    print(id)
    clave_generada = crearClave()  # Llama a la función para generar la clave
    guardarClaveAuditoria(clave_generada, id)
    return clave_generada

# Ruta para crear un área
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

# Ruta para actualizar un área
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
