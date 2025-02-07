# Importandopaquetes desde flask
from flask import session, flash

# Importando conexion a BD
from conexion.conexionBD import connectionBD
# Para  validar contraseña
from werkzeug.security import check_password_hash

import re
# Para encriptar contraseña generate_password_hash
from werkzeug.security import generate_password_hash


def recibeInsertRegisterUser(cedula, name, surname, pass_user, tarjeta, id_area, id_rol, estado, genero):
    respuestaValidar = validarDataRegisterLogin(
        cedula, name, surname, pass_user,tarjeta)

    if (respuestaValidar):
        nueva_password = generate_password_hash(pass_user, method='scrypt')
        try:
            with connectionBD() as conexion_MySQLdb:
                with conexion_MySQLdb.cursor(dictionary=True) as mycursor:
                    sql = """
                    INSERT INTO usuarios(cedula, nombre_usuario, apellido_usuario, password, tarjeta, id_area, id_rol, estado, genero) 
                    VALUES (%s, %s, %s, %s, %s, %s, %s ,%s, %s)
                    """
                    valores = (cedula, name, surname, nueva_password, tarjeta, id_area, id_rol, estado, genero)
                    mycursor.execute(sql, valores)
                    conexion_MySQLdb.commit()
                    resultado_insert = mycursor.rowcount
                    return resultado_insert
        except Exception as e:
            print(f"Error en el Insert users: {e}")
            return []
    else:
        return False


# Validando la data del Registros para el login
def validarDataRegisterLogin(cedula, name, surname, pass_user, tarjeta):
    try:
        with connectionBD() as conexion_MySQLdb:
            with conexion_MySQLdb.cursor(dictionary=True) as cursor:
                 # Validación de la tarjeta
                queryTarjeta ="SELECT * FROM usuarios WHERE tarjeta = %s"
                cursor.execute(queryTarjeta, (tarjeta,))
                tarjetaBD = cursor.fetchone()
                if tarjetaBD is not None:
                    flash('Ya existe una cuenta con esta tarjeta', 'error')
                    return False
                # Validación de la cédula
                queryCedula = "SELECT * FROM usuarios WHERE cedula = %s"
                cursor.execute(queryCedula, (cedula,))
                userBD = cursor.fetchone()

                if userBD is not None:
                    flash('Ya existe una cuenta con este número de cédula', 'error')
                    return False
                # Validar que los campos obligatorios no estén vacíos
                if not cedula or not name or not pass_user or not tarjeta:
                    flash('Por favor llene todos los campos del formulario.', 'error')
                    return False

                # Todos los datos son válidos y no existen en la base de datos
                return True

    except Exception as e:
        print(f"Error en validarDataRegisterLogin: {e}")
        return []



def info_perfil_session(id):
    print(id)
    try:
        with connectionBD() as conexion_MySQLdb:
            with conexion_MySQLdb.cursor(dictionary=True) as cursor:
                querySQL = "SELECT id_usuario, nombre_usuario, apellido_usuario, cedula, id_area, id_rol, tarjeta, estado, genero FROM usuarios WHERE id_usuario = %s"
                cursor.execute(querySQL, (id,))
                info_perfil = cursor.fetchall()
        return info_perfil
    except Exception as e:
        print(f"Error en info_perfil_session : {e}")
        return []


def procesar_update_perfil(data_form,id):
    # Extraer datos del diccionario data_form
    id_user = id
    cedula = data_form['cedula']
    nombre_usuario = data_form['name']
    apellido_usuario = data_form['surname']
    id_area = data_form['selectArea']
    id_rol= data_form['selectRol']
    tarjeta= data_form['tarjeta']
    estado= data_form['estado']
    genero= data_form['genero']

    
    new_pass_user = data_form['new_pass_user']
    

    if session['rol'] == 1 :
        try:
            nueva_password = generate_password_hash(
                new_pass_user, method='scrypt')
            with connectionBD() as conexion_MySQLdb:
                with conexion_MySQLdb.cursor(dictionary=True) as cursor:
                    querySQL = """
                        UPDATE usuarios
                        SET 
                            nombre_usuario = %s,
                            apellido_usuario = %s,
                            id_area = %s,
                            id_rol = %s,
                            tarjeta = %s,
                            estado = %s,
                            genero = %s,
                            password = %s
                        WHERE id_usuario = %s
                    """
                    params = (nombre_usuario,apellido_usuario, id_area, id_rol, tarjeta ,estado, genero,
                                nueva_password, id_user, )
                    cursor.execute(querySQL, params)
                    conexion_MySQLdb.commit()
            return 1
        except Exception as e:
            print(
                f"Ocurrió en procesar_update_perfil: {e}")
            return []
    
    pass_actual = data_form['pass_actual']
    repetir_pass_user = data_form['repetir_pass_user']

    print(id_area+" HOLA "+id_rol)

    if not pass_actual and not new_pass_user and not repetir_pass_user:
            return updatePefilSinPass(id_user, nombre_usuario, apellido_usuario, id_area, id_rol)

    with connectionBD() as conexion_MySQLdb:
        with conexion_MySQLdb.cursor(dictionary=True) as cursor:
            querySQL = """SELECT * FROM usuarios WHERE cedula = %s LIMIT 1"""
            cursor.execute(querySQL, (cedula,))
            account = cursor.fetchone()
            if account:
                
                if check_password_hash(account['password'], pass_actual):
                    # Verificar si new_pass_user y repetir_pass_user están vacías
                        if new_pass_user != repetir_pass_user:
                            return 2
                        else:
                            try:
                                nueva_password = generate_password_hash(
                                    new_pass_user, method='scrypt')
                                with connectionBD() as conexion_MySQLdb:
                                    with conexion_MySQLdb.cursor(dictionary=True) as cursor:
                                        querySQL = """
                                            UPDATE usuarios
                                            SET 
                                                nombre_usuario = %s,
                                                apellido_usuario = %s,
                                                id_area = %s,
                                                password = %s
                                            WHERE id_usuario = %s
                                        """
                                        params = (nombre_usuario,apellido_usuario, id_area,
                                                  nueva_password, id_user)
                                        cursor.execute(querySQL, params)
                                        conexion_MySQLdb.commit()
                                return cursor.rowcount or []
                            except Exception as e:
                                print(
                                    f"Ocurrió en procesar_update_perfil: {e}")
                                return []
            else:
                return 0



def updatePefilSinPass(id_user, nombre_usuario, apellido_usuario, id_area, id_rol):
    try:
        with connectionBD() as conexion_MySQLdb:
            with conexion_MySQLdb.cursor(dictionary=True) as cursor:
                querySQL = """
                    UPDATE usuarios
                    SET 
                        nombre_usuario = %s,
                        apellido_usuario = %s,
                        id_area = %s,
                        id_rol = %s
                    WHERE id_usuario = %s
                """
                params = ( nombre_usuario, apellido_usuario, id_area, id_rol, id_user)
                cursor.execute(querySQL, params)
                conexion_MySQLdb.commit()
        return cursor.rowcount
    except Exception as e:
        print(f"Ocurrió un error en la funcion updatePefilSinPass: {e}")
        return []


def dataLoginSesion():
    inforLogin = {
        "id": session['id'],
        "name": session['name'],
        "cedula": session['cedula'],
        "rol": session['rol']
    }
    return inforLogin
