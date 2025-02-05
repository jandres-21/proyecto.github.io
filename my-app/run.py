import subprocess
import os
from app import app

# Ruta del script que maneja la conexión con Arduino
arduino_script = os.path.join(os.path.dirname(__file__), "conexion/conexion_arduino.py")

# Ejecutar conexion_arduino.py en segundo plano
subprocess.Popen(["python", arduino_script])

# Ejecutar la aplicación Flask en el puerto 8080
if __name__ == '__main__':
    app.debug = True
    app.run(host="0.0.0.0", port=8080)
