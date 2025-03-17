from flask import Flask, render_template, request, redirect, url_for, flash
from db import get_connection
from config import Config

app = Flask(__name__)
app.secret_key = "123456"
app.config.from_object(Config)  # Cargar configuración correctamente

# Ruta principal que muestra el listado de alumnos
@app.route('/')
def home():
    # Obtener la lista de alumnos desde la base de datos
    connection = get_connection()
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT * FROM alumnos")
            alumnos = cursor.fetchall()
    finally:
        connection.close()

    return render_template('home.html', alumnos=alumnos)

# Ruta para el registro de alumnos y asignación de calificaciones
@app.route('/registro', methods=['GET', 'POST'])
def registro():
    if request.method == 'POST':
        nombre = request.form['nombre']
        apellido = request.form['apellido']

        # Insertar el nuevo alumno en la base de datos
        connection = get_connection()
        try:
            with connection.cursor() as cursor:
                cursor.execute("INSERT INTO alumnos (nombre, apellido) VALUES (%s, %s)", (nombre, apellido))
                connection.commit()

                # Obtener el ID del nuevo alumno
                alumno_id = cursor.lastrowid

                # Registrar las calificaciones de las asignaturas seleccionadas
                asignaturas = request.form.getlist('asignaturas')  # Obtener las asignaturas seleccionadas
                for asignatura_id in asignaturas:
                    # Obtener la calificación correspondiente para cada asignatura
                    nota = request.form.get(f'nota_{asignatura_id}')
                    if nota:
                        cursor.execute(""" 
                            INSERT INTO calificaciones (alumno_id, asignatura_id, nota)
                            VALUES (%s, %s, %s)
                        """, (alumno_id, asignatura_id, nota))
                connection.commit()

        finally:
            connection.close()

        return redirect(url_for('home'))

    # Obtener todas las asignaturas desde la base de datos
    connection = get_connection()
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT * FROM asignaturas")
            asignaturas = cursor.fetchall()
    finally:
        connection.close()

    return render_template('registro.html', asignaturas=asignaturas)

# Ruta para mostrar las calificaciones de un alumno y permitir añadir más calificaciones
@app.route('/calificaciones/<int:alumno_id>', methods=['GET', 'POST'])
def calificaciones(alumno_id):
    # Obtener las calificaciones del alumno desde la base de datos
    connection = get_connection()
    try:
        with connection.cursor() as cursor:
            # Obtener el alumno usando alumno_id
            cursor.execute("SELECT * FROM alumnos WHERE id = %s", (alumno_id,))
            alumno = cursor.fetchone()

            # Obtener las calificaciones del alumno para cada asignatura
            cursor.execute(""" 
                SELECT a.nombre, a.apellido, asig.nombre AS asignatura, c.nota, asig.id AS asignatura_id
                FROM calificaciones c
                JOIN alumnos a ON c.alumno_id = a.id
                JOIN asignaturas asig ON c.asignatura_id = asig.id
                WHERE a.id = %s
            """, (alumno_id,))
            calificaciones = cursor.fetchall()

            # Obtener todas las asignaturas disponibles
            cursor.execute("SELECT * FROM asignaturas")
            asignaturas = cursor.fetchall()

            # Crear un diccionario de calificaciones por asignatura_id para actualizar
            calificaciones_dict = {calif['asignatura_id']: calif for calif in calificaciones}

            # Si el formulario ha sido enviado, actualizamos las calificaciones
            if request.method == 'POST':
                for asignatura in asignaturas:
                    # Verificar si hay calificación para la asignatura
                    nota = request.form.get(f'nota_{asignatura["id"]}')
                    if nota:
                        # Verificar si ya existe una calificación para esa asignatura
                        cursor.execute("""
                            SELECT * FROM calificaciones WHERE alumno_id = %s AND asignatura_id = %s
                        """, (alumno_id, asignatura['id']))
                        existing_calif = cursor.fetchone()

                        if existing_calif:
                            # Si ya existe, actualizamos la calificación
                            cursor.execute("""
                                UPDATE calificaciones SET nota = %s WHERE alumno_id = %s AND asignatura_id = %s
                            """, (nota, alumno_id, asignatura['id']))
                        else:
                            # Si no existe, insertamos una nueva calificación
                            cursor.execute("""
                                INSERT INTO calificaciones (alumno_id, asignatura_id, nota)
                                VALUES (%s, %s, %s)
                            """, (alumno_id, asignatura['id'], nota))

                connection.commit()
                flash("¡Calificación guardada con éxito!")

                # Después de actualizar o insertar las calificaciones, obtenemos las calificaciones actualizadas
                cursor.execute(""" 
                    SELECT a.nombre, a.apellido, asig.nombre AS asignatura, c.nota, asig.id AS asignatura_id
                    FROM calificaciones c
                    JOIN alumnos a ON c.alumno_id = a.id
                    JOIN asignaturas asig ON c.asignatura_id = asig.id
                    WHERE a.id = %s
                """, (alumno_id,))
                calificaciones = cursor.fetchall()
                return redirect(url_for('calificaciones', alumno_id=alumno_id))

    finally:
        connection.close()

    return render_template('calificaciones.html', calificaciones=calificaciones, alumno=alumno, asignaturas=asignaturas, calificaciones_dict=calificaciones_dict)

if __name__ == '__main__':
    app.run(host="0.0.0.0", debug=True, port=80)