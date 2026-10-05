from flask import Flask, request, jsonify
from flask_mysqldb import MySQL
from flask_cors import CORS, cross_origin
import os

app = Flask(__name__)

# =========================================================
# CONFIGURACIÓN MYSQL
# =========================================================

app.config["MYSQL_HOST"] = os.environ.get("DB_HOST")
app.config["MYSQL_USER"] = os.environ.get("DB_USER")
app.config["MYSQL_PASSWORD"] = os.environ.get("DB_PASSWORD")
app.config["MYSQL_DB"] = os.environ.get("DB_NAME")

mysql = MySQL(app)

CORS(app)


# =========================================================
# 1. USUARIO
# =========================================================

# CREAR USUARIO
@app.route("/usuario", methods=["POST"])
@cross_origin()
def crear_usuario():

    datos = request.json

    nombre = datos["nombre"]
    apellido = datos["apellido"]
    fecha_nacimiento = datos["fecha_nacimiento"]
    email = datos["email"]
    contrasenia = datos["contrasenia"]
    contexto_aceptado = datos.get("contexto_aceptado", False)

    cursor = mysql.connection.cursor()

    sql = """
        INSERT INTO usuario
        (nombre, apellido, fecha_nacimiento, email, contrasenia, contexto_aceptado)
        VALUES (%s, %s, %s, %s, %s, %s)
    """

    cursor.execute(sql, (
        nombre,
        apellido,
        fecha_nacimiento,
        email,
        contrasenia,
        contexto_aceptado
    ))

    mysql.connection.commit()

    nuevo_id = cursor.lastrowid

    cursor.close()

    return jsonify({
        "resultado": "Usuario creado correctamente",
        "id": nuevo_id
    }), 201


# OBTENER USUARIOS
@app.route("/usuario", methods=["GET"])
@cross_origin()
def obtener_usuarios():

    cursor = mysql.connection.cursor()

    sql = """
        SELECT
            id,
            nombre,
            apellido,
            fecha_nacimiento,
            email,
            contrasenia,
            contexto_aceptado
        FROM usuario
        ORDER BY id ASC
    """

    cursor.execute(sql)

    registros = cursor.fetchall()

    cursor.close()

    usuarios = []

    for usuario in registros:

        usuarios.append({
            "id": usuario[0],
            "nombre": usuario[1],
            "apellido": usuario[2],
            "fecha_nacimiento": usuario[3],
            "email": usuario[4],
            "contrasenia": usuario[5],
            "contexto_aceptado": usuario[6]
        })

    return jsonify(usuarios)


# OBTENER UN USUARIO
@app.route("/usuario/<int:id>", methods=["GET"])
@cross_origin()
def obtener_usuario(id):

    cursor = mysql.connection.cursor()

    sql = """
        SELECT
            id,
            nombre,
            apellido,
            fecha_nacimiento,
            email,
            contrasenia,
            contexto_aceptado
        FROM usuario
        WHERE id = %s
    """

    cursor.execute(sql, (id,))

    usuario = cursor.fetchone()

    cursor.close()

    if usuario is None:
        return jsonify({
            "mensaje": "Usuario no encontrado"
        }), 404

    return jsonify({
        "id": usuario[0],
        "nombre": usuario[1],
        "apellido": usuario[2],
        "fecha_nacimiento": usuario[3],
        "email": usuario[4],
        "contrasenia": usuario[5],
        "contexto_aceptado": usuario[6]
    })


# ELIMINAR USUARIO
@app.route("/usuario/<int:id>", methods=["DELETE"])
@cross_origin()
def eliminar_usuario(id):

    cursor = mysql.connection.cursor()

    sql = "DELETE FROM usuario WHERE id = %s"

    cursor.execute(sql, (id,))

    mysql.connection.commit()

    eliminado = cursor.rowcount

    cursor.close()

    if eliminado == 0:
        return jsonify({
            "mensaje": "Usuario no encontrado"
        }), 404

    return jsonify({
        "resultado": "Usuario eliminado correctamente"
    })


# ACTUALIZAR USUARIO
@app.route("/usuario/<int:id>", methods=["PUT"])
@cross_origin()
def actualizar_usuario(id):

    datos = request.json

    nombre = datos["nombre"]
    apellido = datos["apellido"]
    fecha_nacimiento = datos["fecha_nacimiento"]
    email = datos["email"]
    contrasenia = datos["contrasenia"]
    contexto_aceptado = datos.get("contexto_aceptado", False)

    cursor = mysql.connection.cursor()

    sql = """
        UPDATE usuario
        SET
            nombre = %s,
            apellido = %s,
            fecha_nacimiento = %s,
            email = %s,
            contrasenia = %s,
            contexto_aceptado = %s
        WHERE id = %s
    """

    cursor.execute(sql, (
        nombre,
        apellido,
        fecha_nacimiento,
        email,
        contrasenia,
        contexto_aceptado,
        id
    ))

    mysql.connection.commit()

    actualizado = cursor.rowcount

    cursor.close()

    if actualizado == 0:
        return jsonify({
            "mensaje": "Usuario no encontrado"
        }), 404

    return jsonify({
        "resultado": "Usuario actualizado correctamente"
    })


# =========================================================
# 2. CONDICION
# =========================================================

# OBTENER CONDICIONES
@app.route("/condicion", methods=["GET"])
@cross_origin()
def obtener_condiciones():

    cursor = mysql.connection.cursor()

    sql = """
        SELECT
            id_condicion,
            condicion
        FROM condicion
        ORDER BY id_condicion ASC
    """

    cursor.execute(sql)

    registros = cursor.fetchall()

    cursor.close()

    condiciones = []

    for condicion in registros:

        condiciones.append({
            "id_condicion": condicion[0],
            "condicion": condicion[1]
        })

    return jsonify(condiciones)


# CREAR CONDICION
@app.route("/condicion", methods=["POST"])
@cross_origin()
def crear_condicion():

    datos = request.json

    nombre = datos["condicion"]

    cursor = mysql.connection.cursor()

    sql = """
        INSERT INTO condicion (condicion)
        VALUES (%s)
    """

    cursor.execute(sql, (nombre,))

    mysql.connection.commit()

    nuevo_id = cursor.lastrowid

    cursor.close()

    return jsonify({
        "resultado": "Condición creada correctamente",
        "id_condicion": nuevo_id
    }), 201


# =========================================================
# 3. RECETAS
# =========================================================

# OBTENER RECETAS
@app.route("/recetas", methods=["GET"])
@cross_origin()
def obtener_recetas():

    cursor = mysql.connection.cursor()

    sql = """
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
        ORDER BY r.id_receta ASC
    """

    cursor.execute(sql)

    registros = cursor.fetchall()

    cursor.close()

    recetas = []

    for receta in registros:

        recetas.append({
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

    return jsonify(recetas)


# OBTENER UNA RECETA
@app.route("/recetas/<int:id>", methods=["GET"])
@cross_origin()
def obtener_receta(id):

    cursor = mysql.connection.cursor()

    sql = """
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
    """

    cursor.execute(sql, (id,))

    receta = cursor.fetchone()

    cursor.close()

    if receta is None:
        return jsonify({
            "mensaje": "Receta no encontrada"
        }), 404

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


# CREAR RECETA
@app.route("/recetas", methods=["POST"])
@cross_origin()
def crear_receta():

    datos = request.json

    cursor = mysql.connection.cursor()

    sql = """
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
    """

    cursor.execute(sql, (
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
        "resultado": "Receta creada correctamente",
        "id_receta": nuevo_id
    }), 201


# =========================================================
# 4. REGISTRO GLUCOSA
# =========================================================

@app.route("/registro_glucosa", methods=["GET", "POST"])
@cross_origin()
def registro_glucosa():

    cursor = mysql.connection.cursor()

    # -------------------------
    # POST
    # -------------------------

    if request.method == "POST":

        datos = request.json

        glucosa = datos["glucosa"]
        fecha = datos["fecha"]
        usuario_id = datos["Usuario_id"]
        nota = datos["nota"]
        comentarios = datos.get("comentarios")

        sql = """
            INSERT INTO registro_glucosa
            (
                glucosa,
                fecha,
                Usuario_id,
                nota,
                comentarios
            )
            VALUES (%s, %s, %s, %s, %s)
        """

        cursor.execute(sql, (
            glucosa,
            fecha,
            usuario_id,
            nota,
            comentarios
        ))

        mysql.connection.commit()

        nuevo_id = cursor.lastrowid

        cursor.close()

        return jsonify({
            "resultado": "Glucosa guardada correctamente",
            "id_registro": nuevo_id
        }), 201

    # -------------------------
    # GET
    # -------------------------

    sql = """
        SELECT
            id_registro,
            glucosa,
            fecha,
            Usuario_id,
            nota,
            comentarios
        FROM registro_glucosa
        ORDER BY fecha ASC
    """

    cursor.execute(sql)

    registros = cursor.fetchall()

    cursor.close()

    datos = []

    for registro in registros:

        fecha = registro[2]

        if hasattr(fecha, "strftime"):
            fecha = fecha.strftime("%Y-%m-%d %H:%M:%S")

        datos.append({
            "id_registro": registro[0],
            "glucosa": registro[1],
            "fecha": fecha,
            "Usuario_id": registro[3],
            "nota": registro[4],
            "comentarios": registro[5]
        })

    return jsonify(datos)


# =========================================================
# 5. PLAN SEMANAL
# =========================================================

# OBTENER PLAN SEMANAL
@app.route("/plan_semanal", methods=["GET"])
@cross_origin()
def obtener_plan():

    cursor = mysql.connection.cursor()

    sql = """
        SELECT
            p.id_plan,
            p.Usuario_id,
            p.id_receta,
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
            r.preparacion,
            p.dia,
            p.comida
        FROM plan_semanal p
        INNER JOIN recetas r
            ON p.id_receta = r.id_receta
        ORDER BY
            p.Usuario_id,
            p.id_plan
    """

    cursor.execute(sql)

    registros = cursor.fetchall()

    cursor.close()

    plan = []

    for registro in registros:

        plan.append({
            "id_plan": registro[0],
            "Usuario_id": registro[1],
            "id_receta": registro[2],
            "titulo": registro[3],
            "descripcion": registro[4],
            "imagen": registro[5],
            "porcion": registro[6],
            "calorias": float(registro[7]),
            "proteinas": float(registro[8]),
            "carbohidratos": float(registro[9]),
            "grasas": float(registro[10]),
            "sodio": float(registro[11]),
            "ingredientes": registro[12],
            "preparacion": registro[13],
            "dia": registro[14],
            "comida": registro[15]
        })

    return jsonify(plan)


# CREAR PLAN SEMANAL
@app.route("/plan_semanal", methods=["POST"])
@cross_origin()
def crear_plan():

    datos = request.json

    usuario_id = datos["Usuario_id"]
    id_receta = datos["id_receta"]
    dia = datos["dia"]
    comida = datos["comida"]

    cursor = mysql.connection.cursor()

    sql = """
        INSERT INTO plan_semanal
        (
            Usuario_id,
            id_receta,
            dia,
            comida
        )
        VALUES (%s, %s, %s, %s)
    """

    cursor.execute(sql, (
        usuario_id,
        id_receta,
        dia,
        comida
    ))

    mysql.connection.commit()

    nuevo_id = cursor.lastrowid

    cursor.close()

    return jsonify({
        "resultado": "Plan semanal creado correctamente",
        "id_plan": nuevo_id
    }), 201


# =========================================================
# INICIAR SERVIDOR
# =========================================================

if __name__ == "__main__":

    port = int(os.environ.get("PORT", 5000))

    app.run(
        host="0.0.0.0",
        port=port
    )