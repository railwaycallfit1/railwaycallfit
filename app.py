from flask import Flask, request, jsonify
from flask_mysqldb import MySQL
from flask_cors import CORS, cross_origin
import os
import re
import json
import hmac
import bcrypt
import urllib.request
import urllib.parse

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

# Client ID de Google (el mismo que usa inicioSesion.js). Si querés, podés
# definir GOOGLE_CLIENT_ID como variable en Railway y no hace falta tocar el código.
GOOGLE_CLIENT_ID = env("GOOGLE_CLIENT_ID") or "1082909113641-hmld5pn8nf3pf44fnnpo918h857i67t5.apps.googleusercontent.com"


# ============================================================
# HASHEO DE CONTRASEÑAS (bcrypt)
# ============================================================

def _bytes(contrasenia):
    # bcrypt solo usa los primeros 72 bytes
    return contrasenia.encode("utf-8")[:72]


def hashear_contrasenia(contrasenia):
    return bcrypt.hashpw(_bytes(contrasenia), bcrypt.gensalt()).decode("utf-8")


def es_hash(valor):
    return bool(valor) and valor.startswith(("$2a$", "$2b$", "$2y$"))


def verificar_contrasenia(contrasenia, hash_guardado):
    try:
        return bcrypt.checkpw(_bytes(contrasenia), hash_guardado.encode("utf-8"))
    except (ValueError, AttributeError):
        return False


# ============================================================
# FOTO DE PERFIL
# ============================================================

# La foto se guarda en la columna usuario.foto_perfil (MEDIUMTEXT) como texto:
#  - foto elegida por la persona: "data:image/jpeg;base64,..." (la web y la app la
#    achican a ~256 px antes de enviarla, así que pesa 20-40 KB)
#  - foto de Google: la dirección https://lh3.googleusercontent.com/...
FOTO_MAX_CARACTERES = 400000  # ~300 KB de texto: de sobra para una foto de 256 px

FOTO_DATA_URL = re.compile(r"data:image/(jpeg|png|webp);base64,[A-Za-z0-9+/=]+")


def foto_valida(foto):

    if not isinstance(foto, str) or len(foto) > FOTO_MAX_CARACTERES:
        return False

    # Foto de Google (solo direcciones de Google)
    if foto.startswith("https://"):
        host = urllib.parse.urlparse(foto).hostname or ""
        return host.endswith(".googleusercontent.com")

    # Foto elegida por la persona
    return bool(FOTO_DATA_URL.fullmatch(foto))


# ============================================================
# USUARIO
# ============================================================

# Obtener todos los usuarios (sin contraseña)
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
            contexto_aceptado,
            condiciones,
            contrasenia
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
            "contexto_aceptado": bool(usuario[5]),
            "condiciones": usuario[6] or "",
            "tiene_contrasenia": bool(usuario[7])
        })

    return jsonify(resultado)


# Obtener usuario por ID (sin contraseña)
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
            contexto_aceptado,
            condiciones,
            contrasenia
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
        "contexto_aceptado": bool(usuario[5]),
        "condiciones": usuario[6] or "",
        "tiene_contrasenia": bool(usuario[7])
    })


# Crear usuario
@app.route("/usuario", methods=["POST"])
def crear_usuario():

    datos = request.json

    nombre = datos["nombre"]
    apellido = datos["apellido"]
    fecha_nacimiento = datos["fecha_nacimiento"]
    email = datos["email"]
    contexto_aceptado = datos.get("contexto_aceptado", False)
    condiciones = datos.get("condiciones", "")

    if not datos.get("contrasenia"):
        return jsonify({"error": "La contraseña es obligatoria"}), 400

    # La contraseña se guarda siempre hasheada
    contrasenia = hashear_contrasenia(datos["contrasenia"])

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
    contexto_aceptado = datos.get("contexto_aceptado", False)

    # La contraseña es opcional: si no viene, se conserva la guardada.
    # Si viene en texto plano, se hashea. Si viene ya hasheada, se ignora.
    contrasenia = datos.get("contrasenia")

    if contrasenia and not es_hash(contrasenia):
        contrasenia = hashear_contrasenia(contrasenia)
    else:
        contrasenia = None

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
            contrasenia = COALESCE(%s, contrasenia),
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


# Obtener la foto de perfil de un usuario
# (va en una ruta aparte para que el resto de las respuestas de usuario no
# arrastren la foto, que es lo más pesado)
@app.route("/usuario/<int:id>/foto", methods=["GET"])
def obtener_foto_usuario(id):

    cursor = mysql.connection.cursor()

    cursor.execute(
        "SELECT foto_perfil FROM usuario WHERE id = %s",
        (id,)
    )

    fila = cursor.fetchone()

    cursor.close()

    if not fila:
        return jsonify({"error": "Usuario no encontrado"}), 404

    foto = fila[0]

    if isinstance(foto, bytes):
        foto = foto.decode("utf-8")

    # foto = None cuando todavía no tiene
    return jsonify({"foto": foto or None})


# Guardar o quitar la foto de perfil. No toca ningún otro dato del usuario.
#   body: { "foto": "data:image/jpeg;base64,..." }  -> guarda la foto
#   body: { "foto": null }                          -> la quita
@app.route("/usuario/<int:id>/foto", methods=["PUT"])
def actualizar_foto_usuario(id):

    datos = request.get_json(silent=True) or {}

    foto = datos.get("foto")

    if foto is None or foto == "":
        foto = None
    elif not foto_valida(foto):
        return jsonify({"error": "La foto no es válida o es demasiado grande"}), 400

    cursor = mysql.connection.cursor()

    cursor.execute(
        "UPDATE usuario SET foto_perfil = %s WHERE id = %s",
        (foto, id)
    )

    mysql.connection.commit()

    # rowcount es 0 también cuando la foto ya era la misma, por eso se
    # confirma con un SELECT que el usuario realmente no existe
    if cursor.rowcount == 0:
        cursor.execute("SELECT 1 FROM usuario WHERE id = %s", (id,))
        if cursor.fetchone() is None:
            cursor.close()
            return jsonify({"error": "Usuario no encontrado"}), 404

    cursor.close()

    return jsonify({
        "mensaje": "Foto de perfil actualizada correctamente"
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


# El perfil está completo cuando tiene nombre y apellido (mismo criterio que usa la web)
def perfil_completo(fila):
    return bool((fila[1] or "").strip() and (fila[2] or "").strip())


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
            condiciones,
            contrasenia
        FROM usuario
        WHERE LOWER(email) = %s
    """, (email,))

    fila = cursor.fetchone()

    if not fila:
        cursor.close()
        return jsonify({"error": "Correo o contraseña incorrectos"}), 401

    guardada = fila[7] or ""

    if es_hash(guardada):
        correcta = verificar_contrasenia(contrasenia, guardada)
    else:
        # Usuario viejo con contraseña en texto plano: se compara directo
        # y, si coincide, se hashea en este mismo momento (migración automática)
        correcta = bool(guardada) and hmac.compare_digest(
            guardada.encode("utf-8"),
            contrasenia.encode("utf-8")
        )

        if correcta:
            cursor.execute(
                "UPDATE usuario SET contrasenia = %s WHERE id = %s",
                (hashear_contrasenia(contrasenia), fila[0])
            )
            mysql.connection.commit()

    cursor.close()

    if not correcta:
        return jsonify({"error": "Correo o contraseña incorrectos"}), 401

    return jsonify({
        "mensaje": "Sesión iniciada correctamente",
        "usuario": usuario_publico(fila[:7])
    })


# ============================================================
# LOGIN CON GOOGLE
# ============================================================

# Verifica el token de Google en el servidor y devuelve los datos de la cuenta
# (o None si el token no es válido).
def cuenta_google_desde_token(token):

    if not token or not isinstance(token, str):
        return None

    try:
        if token.count(".") == 2:
            # ID token (JWT): es el que entrega el botón "Iniciar sesión con Google" de la web.
            # Google valida la firma y el vencimiento; nosotros comprobamos que sea para CallFit.
            url = "https://oauth2.googleapis.com/tokeninfo?id_token=" + urllib.parse.quote(token, safe="")

            with urllib.request.urlopen(url, timeout=10) as respuesta:
                cuenta = json.loads(respuesta.read().decode("utf-8"))

            if cuenta.get("aud") != GOOGLE_CLIENT_ID:
                return None

            if str(cuenta.get("email_verified")).lower() != "true":
                return None

        else:
            # Access token (compatibilidad con quien ya lo mandaba así, por ejemplo la app móvil)
            peticion = urllib.request.Request(
                "https://www.googleapis.com/oauth2/v3/userinfo",
                headers={"Authorization": "Bearer " + token}
            )

            with urllib.request.urlopen(peticion, timeout=10) as respuesta:
                cuenta = json.loads(respuesta.read().decode("utf-8"))

    except Exception:
        return None

    email = (cuenta.get("email") or "").strip().lower()

    if not email:
        return None

    return {
        "email": email,
        "nombre": cuenta.get("given_name") or "",
        "apellido": cuenta.get("family_name") or "",
        "foto": cuenta.get("picture") or ""
    }


# Iniciar sesión con Google: el servidor verifica el token y busca el correo en la base.
#  - Existe  -> devuelve el usuario y si ya completó el perfil (entra directo o completa el formulario)
#  - No existe -> 404 con registrado = False (la web manda a completar el formulario)
@app.route("/login/google", methods=["POST"])
def login_google():

    datos = request.json or {}

    token = datos.get("token")

    if not token:
        return jsonify({"error": "Falta el token de Google"}), 400

    cuenta = cuenta_google_desde_token(token)

    if not cuenta:
        return jsonify({"error": "No se pudo verificar la cuenta de Google"}), 401

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
    """, (cuenta["email"],))

    usuario = cursor.fetchone()

    # Si todavía no tiene foto guardada, se guarda la de Google. Si la persona ya
    # eligió una propia, no se pisa. Si algo falla, el inicio de sesión sigue igual.
    if usuario and foto_valida(cuenta["foto"]):
        try:
            cursor.execute("""
                UPDATE usuario
                SET foto_perfil = %s
                WHERE id = %s AND foto_perfil IS NULL
            """, (cuenta["foto"], usuario[0]))
            mysql.connection.commit()
        except Exception:
            mysql.connection.rollback()

    cursor.close()

    if not usuario:
        # Cuenta de Google que todavía no está registrada en CallFit
        return jsonify({
            "error": "Tu cuenta de Google todavía no está registrada",
            "registrado": False,
            "email": cuenta["email"],
            "nombre": cuenta["nombre"],
            "apellido": cuenta["apellido"],
            "foto": cuenta["foto"]
        }), 404

    return jsonify({
        "mensaje": "Sesión iniciada con Google",
        "registrado": True,
        "perfil_completo": perfil_completo(usuario),
        "foto": cuenta["foto"],
        "usuario": usuario_publico(usuario)
    })


# Crear la cuenta de una persona que entró con Google y completó el formulario.
# El correo sale del token verificado (nunca del cuerpo del pedido). La contraseña
# que la persona elige en el formulario es obligatoria y se guarda hasheada.
@app.route("/login/google/registro", methods=["POST"])
def registro_google():

    datos = request.json or {}

    cuenta = cuenta_google_desde_token(datos.get("token"))

    if not cuenta:
        return jsonify({"error": "No se pudo verificar la cuenta de Google"}), 401

    nombre = (datos.get("nombre") or "").strip()
    apellido = (datos.get("apellido") or "").strip()
    fecha_nacimiento = (datos.get("fecha_nacimiento") or "").strip()
    contexto_aceptado = bool(datos.get("contexto_aceptado", False))
    condiciones = datos.get("condiciones") or ""

    # La contraseña es obligatoria: se guarda siempre hasheada
    contrasenia_plana = datos.get("contrasenia") or ""

    if not nombre or not apellido or not fecha_nacimiento:
        return jsonify({"error": "Completá nombre, apellido y fecha de nacimiento"}), 400

    if not contrasenia_plana:
        return jsonify({"error": "La contraseña es obligatoria"}), 400

    if len(contrasenia_plana) < 8:
        return jsonify({"error": "La contraseña debe tener al menos 8 caracteres"}), 400

    contrasenia_guardar = hashear_contrasenia(contrasenia_plana)

    email = cuenta["email"]

    cursor = mysql.connection.cursor()

    # No permitir dos cuentas con el mismo correo
    cursor.execute(
        "SELECT id FROM usuario WHERE LOWER(email) = %s",
        (email,)
    )

    if cursor.fetchone():
        cursor.close()
        return jsonify({"error": "Ya existe una cuenta con ese correo"}), 409

    # Se guarda el hash de la contraseña que eligió (la cuenta también se puede abrir con Google)
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
        contrasenia_guardar,
        contexto_aceptado,
        condiciones
    ))

    mysql.connection.commit()

    nuevo_id = cursor.lastrowid

    # La foto de Google queda guardada desde el primer momento. Si falla, la
    # cuenta se crea igual.
    if foto_valida(cuenta["foto"]):
        try:
            cursor.execute(
                "UPDATE usuario SET foto_perfil = %s WHERE id = %s",
                (cuenta["foto"], nuevo_id)
            )
            mysql.connection.commit()
        except Exception:
            mysql.connection.rollback()

    cursor.close()

    return jsonify({
        "mensaje": "Usuario creado correctamente",
        "usuario": {
            "id": nuevo_id,
            "nombre": nombre,
            "apellido": apellido,
            "fecha_nacimiento": fecha_nacimiento,
            "email": email,
            "contexto_aceptado": contexto_aceptado,
            "condiciones": condiciones
        }
    }), 201


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