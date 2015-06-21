#!/usr/bin/env python

from flask import Flask, jsonify, session, request
import zerodb

PORT = 2015
HOST = "127.0.0.1"
DEBUG = True
DEV_SECRET_KEY = "development key"

app = Flask(__name__)
dbs = {}


@app.route("/_connect", methods=["GET", "POST"])
def connnect():
    if request.method == "GET":
        username = request.args.get("username")
        passphrase = request.args.get("passphrase")
        socket = request.args.get("socket")

    elif request.method == "POST":
        username = request.form.get("username")
        passphrase = request.form.get("passphrase")
        socket = request.form.get("socket")

    else:
        return jsonify(ok=0)

    if not (username and passphrase and socket):
        return jsonify(ok=0, message="Incomplete login information")

    try:
        db = zerodb.DB(socket, username=username, password=passphrase)
    except Exception, e:
        return jsonify(ok=0, message=str(e))

    session["username"] = username
    dbs[username] = db

    return jsonify(ok=1)


@app.route("/<table_name>/_find")
def find(table_name):
    return jsonify(hello="world")


@app.route("/_disconnect")
def disconnect():
    if "username" in session:
        username = session.pop("username")
        if username in dbs:
            del dbs[username]
    return jsonify(ok=1)


if __name__ == "__main__":
    app.config["SECRET_KEY"] = DEV_SECRET_KEY
    app.run(host=HOST, port=PORT, debug=DEBUG)
