from flask import Flask, request, jsonify
from flask_mysqldb import MySQL
from flask_cors import CORS, cross_origin
import os
import json
import urllib.request

app = Flask(__name__)

# =========================
# CONFIGURACIÓN MYSQL
# =========================
def env(nombre):
    return (os.environ.get(nombre) or "").strip()

app.config["MYSQL_HOST"] = os.environ.get("DB_HOST")
app.config["MYSQL_USER"] = os.environ.get("DB_USER")
app.config["MYSQL_PASSWORD"] = os.environ.get("DB_PASSWORD")
app.config["MYSQL_DB"] = os.environ.get("DB_NAME")

mysql = MySQL(app)

CORS(app)


# ============================================================
# USUARIO
# ============================================================

# Obtener todos los usuarios
@app.route("/usuario", methods=["GET"])
def obtener_usuarios():

    cursor = mysql.connection.cursor()

    cursor.execute("""
        SELECT
            id,
            nombre,
            apellido,
            fecha_nacimiento,
            email,
            contrasenia,
            contexto_aceptado,
            condiciones
        FROM usuario
    """)

    usuarios = cursor.fetchall()

    cursor.close()

    resultado = []

    for usuario in usuarios:
        resultado.append({
            "id": usuario[0],
            "nombre": usuario[1],
            "apellido": usuario[2],
            "fecha_nacimiento": str(usuario[3]),
            "email": usuario[4],
            "contrasenia": usuario[5],
            "contexto_aceptado": bool(usuario[6]),
            "condiciones": usuario[7] or ""
        })

    return jsonify(resultado)


# Obtener usuario por ID
@app.route("/usuario/<int:id>", methods=["GET"])
def obtener_usuario(id):

    cursor = mysql.connection.cursor()

    cursor.execute("""
        SELECT
            id,
            nombre,
            apellido,
            fecha_nacimiento,
            email,
            contrasenia,
            contexto_aceptado,
            condiciones
        FROM usuario
        WHERE id = %s
    """, (id,))

    usuario = cursor.fetchone()

    cursor.close()

    if not usuario:
        return jsonify({"error": "Usuario no encontrado"}), 404

    return jsonify({
        "id": usuario[0],
        "nombre": usuario[1],
        "apellido": usuario[2],
        "fecha_nacimiento": str(usuario[3]),
        "email": usuario[4],
        "contrasenia": usuario[5],
        "contexto_aceptado": bool(usuario[6]),
        "condiciones": usuario[7] or ""
    })


# Crear usuario
@app.route("/usuario", methods=["POST"])
def crear_usuario():

    datos = request.json

    nombre = datos["nombre"]
    apellido = datos["apellido"]
    fecha_nacimiento = datos["fecha_nacimiento"]
    email = datos["email"]
    contrasenia = datos["contrasenia"]
    contexto_aceptado = datos.get("contexto_aceptado", False)
    condiciones = datos.get("condiciones", "")

    email = email.strip()

    cursor = mysql.connection.cursor()

    # No permitir dos cuentas con el mismo correo (sin importar mayúsculas)
    cursor.execute(
        "SELECT id FROM usuario WHERE LOWER(email) = %s",
        (email.lower(),)
    )

    if cursor.fetchone():
        cursor.close()
        return jsonify({"error": "Ya existe una cuenta con ese correo"}), 409

    cursor.execute("""
        INSERT INTO usuario
        (
            nombre,
            apellido,
            fecha_nacimiento,
            email,
            contrasenia,
            contexto_aceptado,
            condiciones
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s)
    """, (
        nombre,
        apellido,
        fecha_nacimiento,
        email,
        contrasenia,
        contexto_aceptado,
        condiciones
    ))

    mysql.connection.commit()

    nuevo_id = cursor.lastrowid

    cursor.close()

    return jsonify({
        "mensaje": "Usuario creado correctamente",
        "id": nuevo_id
    }), 201


# Actualizar usuario
@app.route("/usuario/<int:id>", methods=["PUT"])
def actualizar_usuario(id):

    datos = request.json

    nombre = datos["nombre"]
    apellido = datos["apellido"]
    fecha_nacimiento = datos["fecha_nacimiento"]
    email = datos["email"]
    contrasenia = datos["contrasenia"]
    contexto_aceptado = datos.get("contexto_aceptado", False)

    # None = el cliente no mandó el campo: se conservan las condiciones guardadas
    condiciones = datos.get("condiciones")

    email = email.strip()

    cursor = mysql.connection.cursor()

    # El correo no puede ser el de otro usuario
    cursor.execute(
        "SELECT id FROM usuario WHERE LOWER(email) = %s AND id <> %s",
        (email.lower(), id)
    )

    if cursor.fetchone():
        cursor.close()
        return jsonify({"error": "Ya existe una cuenta con ese correo"}), 409

    cursor.execute("""
        UPDATE usuario
        SET
            nombre = %s,
            apellido = %s,
            fecha_nacimiento = %s,
            email = %s,
            contrasenia = %s,
            contexto_aceptado = %s,
            condiciones = COALESCE(%s, condiciones)
        WHERE id = %s
    """, (
        nombre,
        apellido,
        fecha_nacimiento,
        email,
        contrasenia,
        contexto_aceptado,
        condiciones,
        id
    ))

    mysql.connection.commit()

    # rowcount es 0 también cuando no cambió ningún dato, por eso
    # se confirma con un SELECT que el usuario realmente no existe
    if cursor.rowcount == 0:
        cursor.execute("SELECT 1 FROM usuario WHERE id = %s", (id,))
        if cursor.fetchone() is None:
            cursor.close()
            return jsonify({"error": "Usuario no encontrado"}), 404

    cursor.close()

    return jsonify({
        "mensaje": "Usuario actualizado correctamente"
    })


# Datos del usuario que se devuelven al iniciar sesión (nunca la contraseña)
def usuario_publico(fila):
    return {
        "id": fila[0],
        "nombre": fila[1],
        "apellido": fila[2],
        "fecha_nacimiento": str(fila[3]),
        "email": fila[4],
        "contexto_aceptado": bool(fila[5]),
        "condiciones": fila[6] or ""
    }


# Iniciar sesión con correo y contraseña
@app.route("/login", methods=["POST"])
def login():

    datos = request.json or {}

    email = (datos.get("email") or "").strip().lower()
    contrasenia = datos.get("contrasenia") or ""

    if not email or not contrasenia:
        return jsonify({"error": "Ingresá tu correo y tu contraseña"}), 400

    cursor = mysql.connection.cursor()

    cursor.execute("""
        SELECT
            id,
            nombre,
            apellido,
            fecha_nacimiento,
            email,
            contexto_aceptado,
            condiciones
        FROM usuario
        WHERE LOWER(email) = %s AND contrasenia = %s
    """, (email, contrasenia))

    usuario = cursor.fetchone()

    cursor.close()

    if not usuario:
        return jsonify({"error": "Correo o contraseña incorrectos"}), 401

    return jsonify({
        "mensaje": "Sesión iniciada correctamente",
        "usuario": usuario_publico(usuario)
    })


# Iniciar sesión con Google: el servidor verifica el token con Google
@app.route("/login/google", methods=["POST"])
def login_google():

    datos = request.json or {}

    token = datos.get("token")

    if not token:
        return jsonify({"error": "Falta el token de Google"}), 400

    try:
        peticion = urllib.request.Request(
            "https://www.googleapis.com/oauth2/v3/userinfo",
            headers={"Authorization": "Bearer " + token}
        )

        with urllib.request.urlopen(peticion, timeout=10) as respuesta:
            cuenta_google = json.loads(respuesta.read().decode("utf-8"))

    except Exception:
        return jsonify({"error": "No se pudo verificar la cuenta de Google"}), 401

    email = (cuenta_google.get("email") or "").strip().lower()

    if not email:
        return jsonify({"error": "La cuenta de Google no tiene correo"}), 401

    cursor = mysql.connection.cursor()

    cursor.execute("""
        SELECT
            id,
            nombre,
            apellido,
            fecha_nacimiento,
            email,
            contexto_aceptado,
            condiciones
        FROM usuario
        WHERE LOWER(email) = %s
    """, (email,))

    usuario = cursor.fetchone()

    cursor.close()

    if not usuario:
        # Cuenta de Google que todavía no está registrada en CallFit
        return jsonify({
            "error": "Tu cuenta de Google todavía no está registrada",
            "registrado": False,
            "email": email,
            "nombre": cuenta_google.get("given_name") or "",
            "apellido": cuenta_google.get("family_name") or ""
        }), 404

    return jsonify({
        "mensaje": "Sesión iniciada con Google",
        "usuario": usuario_publico(usuario)
    })


# Eliminar usuario
@app.route("/usuario/<int:id>", methods=["DELETE"])
def eliminar_usuario(id):

    cursor = mysql.connection.cursor()

    cursor.execute(
        "DELETE FROM usuario WHERE id = %s",
        (id,)
    )

    mysql.connection.commit()

    if cursor.rowcount == 0:
        cursor.close()
        return jsonify({"error": "Usuario no encontrado"}), 404

    cursor.close()

    return jsonify({
        "mensaje": "Usuario eliminado correctamente"
    })


# ============================================================
# CONDICION
# ============================================================

# Obtener condiciones
@app.route("/condicion", methods=["GET"])
def obtener_condiciones():

    cursor = mysql.connection.cursor()

    cursor.execute("""
        SELECT id_condicion, condicion
        FROM condicion
    """)

    condiciones = cursor.fetchall()

    cursor.close()

    resultado = []

    for condicion in condiciones:
        resultado.append({
            "id_condicion": condicion[0],
            "condicion": condicion[1]
        })

    return jsonify(resultado)


# Crear condición
@app.route("/condicion", methods=["POST"])
def crear_condicion():

    datos = request.json

    condicion = datos["condicion"]

    cursor = mysql.connection.cursor()

    cursor.execute("""
        INSERT INTO condicion (condicion)
        VALUES (%s)
    """, (condicion,))

    mysql.connection.commit()

    nuevo_id = cursor.lastrowid

    cursor.close()

    return jsonify({
        "mensaje": "Condición creada correctamente",
        "id_condicion": nuevo_id
    }), 201


# Actualizar condición
@app.route("/condicion/<int:id>", methods=["PUT"])
def actualizar_condicion(id):

    datos = request.json
    condicion = datos["condicion"]

    cursor = mysql.connection.cursor()

    cursor.execute("""
        UPDATE condicion
        SET condicion = %s
        WHERE id_condicion = %s
    """, (condicion, id))

    mysql.connection.commit()

    if cursor.rowcount == 0:
        cursor.close()
        return jsonify({"error": "Condición no encontrada"}), 404

    cursor.close()

    return jsonify({
        "mensaje": "Condición actualizada correctamente"
    })


# Eliminar condición
@app.route("/condicion/<int:id>", methods=["DELETE"])
def eliminar_condicion(id):

    cursor = mysql.connection.cursor()

    cursor.execute("""
        DELETE FROM condicion
        WHERE id_condicion = %s
    """, (id,))

    mysql.connection.commit()

    if cursor.rowcount == 0:
        cursor.close()
        return jsonify({"error": "Condición no encontrada"}), 404

    cursor.close()

    return jsonify({
        "mensaje": "Condición eliminada correctamente"
    })


# ============================================================
# RECETAS
# ============================================================

# Obtener todas las recetas
@app.route("/recetas", methods=["GET"])
def obtener_recetas():

    cursor = mysql.connection.cursor()

    cursor.execute("""
        SELECT
            r.id_receta,
            r.titulo,
            r.descripcion,
            r.imagen,
            r.porcion,
            r.calorias,
            r.proteinas,
            r.carbohidratos,
            r.grasas,
            r.sodio,
            r.id_condicion,
            c.condicion,
            r.ingredientes,
            r.preparacion
        FROM recetas r
        INNER JOIN condicion c
            ON r.id_condicion = c.id_condicion
    """)

    recetas = cursor.fetchall()

    cursor.close()

    resultado = []

    for receta in recetas:
        resultado.append({
            "id_receta": receta[0],
            "titulo": receta[1],
            "descripcion": receta[2],
            "imagen": receta[3],
            "porcion": receta[4],
            "calorias": float(receta[5]),
            "proteinas": float(receta[6]),
            "carbohidratos": float(receta[7]),
            "grasas": float(receta[8]),
            "sodio": float(receta[9]),
            "id_condicion": receta[10],
            "condicion": receta[11],
            "ingredientes": receta[12],
            "preparacion": receta[13]
        })

    return jsonify(resultado)


# Obtener receta por ID
@app.route("/recetas/<int:id>", methods=["GET"])
def obtener_receta(id):

    cursor = mysql.connection.cursor()

    cursor.execute("""
        SELECT
            r.id_receta,
            r.titulo,
            r.descripcion,
            r.imagen,
            r.porcion,
            r.calorias,
            r.proteinas,
            r.carbohidratos,
            r.grasas,
            r.sodio,
            r.id_condicion,
            c.condicion,
            r.ingredientes,
            r.preparacion
        FROM recetas r
        INNER JOIN condicion c
            ON r.id_condicion = c.id_condicion
        WHERE r.id_receta = %s
    """, (id,))

    receta = cursor.fetchone()

    cursor.close()

    if not receta:
        return jsonify({"error": "Receta no encontrada"}), 404

    return jsonify({
        "id_receta": receta[0],
        "titulo": receta[1],
        "descripcion": receta[2],
        "imagen": receta[3],
        "porcion": receta[4],
        "calorias": float(receta[5]),
        "proteinas": float(receta[6]),
        "carbohidratos": float(receta[7]),
        "grasas": float(receta[8]),
        "sodio": float(receta[9]),
        "id_condicion": receta[10],
        "condicion": receta[11],
        "ingredientes": receta[12],
        "preparacion": receta[13]
    })


# Crear receta
@app.route("/recetas", methods=["POST"])
def crear_receta():

    datos = request.json

    cursor = mysql.connection.cursor()

    cursor.execute("""
        INSERT INTO recetas
        (
            titulo,
            descripcion,
            imagen,
            porcion,
            calorias,
            proteinas,
            carbohidratos,
            grasas,
            sodio,
            id_condicion,
            ingredientes,
            preparacion
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    """, (
        datos["titulo"],
        datos.get("descripcion"),
        datos.get("imagen"),
        datos["porcion"],
        datos["calorias"],
        datos["proteinas"],
        datos["carbohidratos"],
        datos["grasas"],
        datos["sodio"],
        datos["id_condicion"],
        datos["ingredientes"],
        datos["preparacion"]
    ))

    mysql.connection.commit()

    nuevo_id = cursor.lastrowid

    cursor.close()

    return jsonify({
        "mensaje": "Receta creada correctamente",
        "id_receta": nuevo_id
    }), 201


# Actualizar receta
@app.route("/recetas/<int:id>", methods=["PUT"])
def actualizar_receta(id):

    datos = request.json

    cursor = mysql.connection.cursor()

    cursor.execute("""
        UPDATE recetas
        SET
            titulo = %s,
            descripcion = %s,
            imagen = %s,
            porcion = %s,
            calorias = %s,
            proteinas = %s,
            carbohidratos = %s,
            grasas = %s,
            sodio = %s,
            id_condicion = %s,
            ingredientes = %s,
            preparacion = %s
        WHERE id_receta = %s
    """, (
        datos["titulo"],
        datos.get("descripcion"),
        datos.get("imagen"),
        datos["porcion"],
        datos["calorias"],
        datos["proteinas"],
        datos["carbohidratos"],
        datos["grasas"],
        datos["sodio"],
        datos["id_condicion"],
        datos["ingredientes"],
        datos["preparacion"],
        id
    ))

    mysql.connection.commit()

    if cursor.rowcount == 0:
        cursor.close()
        return jsonify({"error": "Receta no encontrada"}), 404

    cursor.close()

    return jsonify({
        "mensaje": "Receta actualizada correctamente"
    })


# Eliminar receta
@app.route("/recetas/<int:id>", methods=["DELETE"])
def eliminar_receta(id):

    cursor = mysql.connection.cursor()

    cursor.execute("""
        DELETE FROM recetas
        WHERE id_receta = %s
    """, (id,))

    mysql.connection.commit()

    if cursor.rowcount == 0:
        cursor.close()
        return jsonify({"error": "Receta no encontrada"}), 404

    cursor.close()

    return jsonify({
        "mensaje": "Receta eliminada correctamente"
    })


# ============================================================
# REGISTRO DE GLUCOSA
# ============================================================

# Obtener registros
@app.route("/registro_glucosa", methods=["GET"])
def obtener_registros_glucosa():

    cursor = mysql.connection.cursor()

    cursor.execute("""
        SELECT
            id_registro,
            glucosa,
            fecha,
            Usuario_id,
            nota,
            comentarios
        FROM registro_glucosa
        ORDER BY fecha DESC
    """)

    registros = cursor.fetchall()

    cursor.close()

    resultado = []

    for registro in registros:
        resultado.append({
            "id_registro": registro[0],
            "glucosa": registro[1],
            "fecha": registro[2].strftime("%Y-%m-%d %H:%M:%S"),
            "Usuario_id": registro[3],
            "nota": registro[4],
            "comentarios": registro[5]
        })

    return jsonify(resultado)


# Crear registro
@app.route("/registro_glucosa", methods=["POST"])
@cross_origin()
def crear_registro_glucosa():

    datos = request.json

    cursor = mysql.connection.cursor()

    cursor.execute("""
        INSERT INTO registro_glucosa
        (
            glucosa,
            fecha,
            Usuario_id,
            nota,
            comentarios
        )
        VALUES (%s, %s, %s, %s, %s)
    """, (
        datos["glucosa"],
        datos["fecha"],
        datos["Usuario_id"],
        datos["nota"],
        datos.get("comentarios")
    ))

    mysql.connection.commit()

    nuevo_id = cursor.lastrowid

    cursor.close()

    return jsonify({
        "mensaje": "Registro de glucosa creado correctamente",
        "id_registro": nuevo_id
    }), 201


# Actualizar registro de glucosa
@app.route("/registro_glucosa/<int:id>", methods=["PUT"])
def actualizar_registro_glucosa(id):

    datos = request.json

    cursor = mysql.connection.cursor()

    cursor.execute("""
        UPDATE registro_glucosa
        SET
            glucosa = %s,
            fecha = %s,
            Usuario_id = %s,
            nota = %s,
            comentarios = %s
        WHERE id_registro = %s
    """, (
        datos["glucosa"],
        datos["fecha"],
        datos["Usuario_id"],
        datos["nota"],
        datos.get("comentarios"),
        id
    ))

    mysql.connection.commit()

    if cursor.rowcount == 0:
        cursor.close()
        return jsonify({"error": "Registro no encontrado"}), 404

    cursor.close()

    return jsonify({
        "mensaje": "Registro de glucosa actualizado correctamente"
    })


# Eliminar registro de glucosa
@app.route("/registro_glucosa/<int:id>", methods=["DELETE"])
def eliminar_registro_glucosa(id):

    cursor = mysql.connection.cursor()

    cursor.execute("""
        DELETE FROM registro_glucosa
        WHERE id_registro = %s
    """, (id,))

    mysql.connection.commit()

    if cursor.rowcount == 0:
        cursor.close()
        return jsonify({"error": "Registro no encontrado"}), 404

    cursor.close()

    return jsonify({
        "mensaje": "Registro de glucosa eliminado correctamente"
    })


# ============================================================
# PLAN SEMANAL
# ============================================================

# Obtener plan semanal
@app.route("/plan_semanal", methods=["GET"])
def obtener_plan_semanal():

    cursor = mysql.connection.cursor()

    cursor.execute("""
        SELECT
            p.id_plan,
            p.Usuario_id,
            p.id_receta,
            p.dia,
            p.comida,
            r.titulo,
            r.descripcion,
            r.imagen,
            r.porcion,
            r.calorias,
            r.proteinas,
            r.carbohidratos,
            r.grasas,
            r.sodio,
            r.ingredientes,
            r.preparacion
        FROM plan_semanal p
        INNER JOIN recetas r
            ON p.id_receta = r.id_receta
        ORDER BY p.id_plan
    """)

    planes = cursor.fetchall()

    cursor.close()

    resultado = []

    for plan in planes:
        resultado.append({
            "id_plan": plan[0],
            "Usuario_id": plan[1],
            "id_receta": plan[2],
            "dia": plan[3],
            "comida": plan[4],
            "titulo": plan[5],
            "descripcion": plan[6],
            "imagen": plan[7],
            "porcion": plan[8],
            "calorias": float(plan[9]),
            "proteinas": float(plan[10]),
            "carbohidratos": float(plan[11]),
            "grasas": float(plan[12]),
            "sodio": float(plan[13]),
            "ingredientes": plan[14],
            "preparacion": plan[15]
        })

    return jsonify(resultado)


# Crear plan semanal
@app.route("/plan_semanal", methods=["POST"])
def crear_plan_semanal():

    datos = request.json

    cursor = mysql.connection.cursor()

    cursor.execute("""
        INSERT INTO plan_semanal
        (
            Usuario_id,
            id_receta,
            dia,
            comida
        )
        VALUES (%s, %s, %s, %s)
    """, (
        datos["Usuario_id"],
        datos["id_receta"],
        datos["dia"],
        datos["comida"]
    ))

    mysql.connection.commit()

    nuevo_id = cursor.lastrowid

    cursor.close()

    return jsonify({
        "mensaje": "Plan semanal creado correctamente",
        "id_plan": nuevo_id
    }), 201


# Actualizar plan semanal
@app.route("/plan_semanal/<int:id>", methods=["PUT"])
def actualizar_plan_semanal(id):

    datos = request.json

    cursor = mysql.connection.cursor()

    cursor.execute("""
        UPDATE plan_semanal
        SET
            Usuario_id = %s,
            id_receta = %s,
            dia = %s,
            comida = %s
        WHERE id_plan = %s
    """, (
        datos["Usuario_id"],
        datos["id_receta"],
        datos["dia"],
        datos["comida"],
        id
    ))

    mysql.connection.commit()

    if cursor.rowcount == 0:
        cursor.close()
        return jsonify({"error": "Plan no encontrado"}), 404

    cursor.close()

    return jsonify({
        "mensaje": "Plan semanal actualizado correctamente"
    })


# Eliminar plan semanal
@app.route("/plan_semanal/<int:id>", methods=["DELETE"])
def eliminar_plan_semanal(id):

    cursor = mysql.connection.cursor()

    cursor.execute("""
        DELETE FROM plan_semanal
        WHERE id_plan = %s
    """, (id,))

    mysql.connection.commit()

    if cursor.rowcount == 0:
        cursor.close()
        return jsonify({"error": "Plan no encontrado"}), 404

    cursor.close()

    return jsonify({
        "mensaje": "Plan semanal eliminado correctamente"
    })


# ============================================================
# INICIAR SERVIDOR
# ============================================================

if __name__ == "__main__":

    port = int(os.environ.get("PORT", 5000))

    app.run(
        host="0.0.0.0",
        port=port
    )