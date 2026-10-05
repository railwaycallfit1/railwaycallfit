from flask import Flask, request, jsonify
from flask.helpers import make_response
from flask_mysqldb import MySQL
from flask_cors import CORS, cross_origin


# para subir archivos
import os
#from werkzeug.utils import secure_filename


app = Flask(__name__)

import os

app.config["MYSQL_HOST"] = os.environ.get("DB_HOST") #"127.0.0.1" 
app.config["MYSQL_USER"] = os.environ.get("DB_USER") #"root" 
app.config["MYSQL_PASSWORD"] = os.environ.get("DB_PASSWORD") #"aula07" 
app.config["MYSQL_DB"] = os.environ.get("DB_NAME") #"callfit" 

mysql = MySQL(app)

CORS(app)


@app.route("/nuevo_usuario", methods=["POST"])
@cross_origin()
def insertar_usuario():
    nombre = request.json["nombre"]
    apellido = request.json["apellido"]
    provincia = request.json["provincia"]

    cursor = mysql.connection.cursor()

    sql = "INSERT INTO Usuarios(nombre, apellido, provincia) values(%s, %s, %s);"
    cursor.execute(sql, (nombre, apellido, provincia))


    mysql.connection.commit()

    cursor.close()
    response = make_response()

    response = jsonify({"resultado":"Agregado nuevo usuario"})
    return response

@app.route("/traer_usuarios", methods=["GET"])
@cross_origin()
def listar_jugadores():
    #consulta SQL
    sql = "SELECT idUsuarios, nombre, apellido, provincia FROM Usuarios"

    #crear el cursor
    cursor = mysql.connection.cursor()#mysql.connect.cursor()
    cursor.execute(sql)

    resultado = cursor.fetchall()

    #cerrar la conexión
    cursor.close()
    response = make_response()

    if resultado == None:
        response = jsonify({"mensaje":None})
        return response
    else:
        usuarios = []

        for i in resultado:

            p = {"id":i[0], "nombre":i[1], "apellido":i[2], "provincia":i[3]}
            usuarios.append(p)

        return jsonify(usuarios)


@cross_origin
@app.route("/eliminar_usuario/<id>", methods=["DELETE"])
def eliminar_usuario(id):

    sql = "DELETE FROM Usuarios WHERE idUsuarios=%s"

    #crear el cursor
    cursor = mysql.connection.cursor()
    cursor.execute(sql, (id,))

    mysql.connection.commit()

    #cerrar la conexión
    cursor.close()
    response = make_response()


    response = jsonify({"resultado":"Usuario eliminado"})
    return response


@cross_origin
@app.route("/actualizar_usuario/<id>", methods=["PUT"])
def actualizar_usuario(id):
    nombre = request.json["nom"]

    sql = "UPDATE Usuarios SET nombre=%s WHERE idUsuarios=%s"

    #crear el cursor
    cursor = mysql.connection.cursor()
    cursor.execute(sql, (nombre, id))
    mysql.connection.commit()


    #cerrar la conexión
    cursor.close()
    response = make_response()

    response = jsonify({"resultado":"Usuario no activo"})
    return response

##############################################################

#PROYECTO


@app.route("/nuevo_recetas", methods=["POST"])
@cross_origin()
def insertar_recetas():
    iddieta = request.json["dieta"]
    nombrereceta = request.json["nombre"]
    descripcion = request.json["descripcion"]
    carbohidrato = request.json["carbohidrato"]
    proteina = request.json["proteina"]
    condicion = request.json["condicion"]
    

    cursor = mysql.connection.cursor()

    sql = "INSERT INTO Dietas(id_dieta, nombre, descripcion, filtro_carbohidratos, filtro_proteina, filtro_condicion) values(%s, %s, %s, %s, %s, %s);"
    cursor.execute(sql, (iddieta, nombrereceta, descripcion, carbohidrato, proteina, condicion))


    mysql.connection.commit()

    cursor.close()
    response = make_response()

    response = jsonify({"resultado":"Agregado nueva receta"})
    return response


#########################################################################

#USUARIO


@app.route("/registro_glucosa", methods=["POST"])
@cross_origin()
def insertar_usuarios():
    glucosa = request.json["glucosa"]
    fecha = request.json["fecha"]
    nota = request.json["nota"]
    comentarios = request.json["comentarios"]
    Usuarioid = request.json["Usuario_id"]
    

    cursor = mysql.connection.cursor()

    sql = "INSERT INTO Registro_glucosa(glucosa, fecha, Usuario_id, nota, comentarios, ) values(%s, %s, %s, %s, %s);"
    cursor.execute(sql, (glucosa, fecha, Usuarioid, nota, comentarios, ))

    #hola

    mysql.connection.commit()

    cursor.close()
    response = make_response()

    response = jsonify({"resultado":"glucosa guardad"})
    return response



@app.route("/traer_recetas", methods=["GET"])
@cross_origin()
def listar_recetas():
    #consulta SQL
    sql = "SELECT id_dieta, nombre, descripcion, filtro_carbohidratos, filtro_proteina, filtro_condicion FROM Dietas"

    #crear el cursor
    cursor = mysql.connection.cursor()#mysql.connect.cursor()
    cursor.execute(sql)

    resultado = cursor.fetchall()

    #cerrar la conexión
    cursor.close()
    response = make_response()

    if resultado == None:
        response = jsonify({"mensaje":None})
        return response
    else:
        usuarios = []

        for i in resultado:

            p = {"id_dieta":i[0], "nombre":i[1], "descripcion":i[2], "filtro_carbohidratos":i[3], "filtro_proteina":i[4], "filtro_condicion":i[5]}
            usuarios.append(p)

        return jsonify(usuarios)




    #REGISTRAR GLUCOSA

@app.route("/registro_glucosa", methods=["GET", "POST"])
@cross_origin()
def registrar_glucosa():

    cursor = mysql.connection.cursor()

    # =========================
    # GUARDAR REGISTRO - POST
    # =========================
    if request.method == "POST":

        glucosa = request.json["glucosa"]
        fecha = request.json["fecha"]
        nota = request.json["nota"]
        comentarios = request.json["comentarios"]
        Usuario_id = request.json["Usuario_id"]

        sql = """
           INSERT INTO Registro_glucosa(glucosa, fecha, Usuario_id, nota, comentarios) values(%s, %s, %s,%s,%s);
        """

        cursor.execute(
            sql,
            (glucosa, fecha, Usuario_id, nota, comentarios)
        )

        mysql.connection.commit()

        cursor.close()

        return jsonify({
            "resultado": "glucosa guardad"
        })


    # =========================
    # OBTENER REGISTROS - GET
    # =========================
    if request.method == "GET":

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

            datos.append({
                "id_registro": registro[0],
                "glucosa": registro[1],
                "fecha": registro[2],
                "Usuario_id": registro[3],
                "nota": registro[4],
                "comentarios": registro[5]
            })

        return jsonify(datos)




if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)


