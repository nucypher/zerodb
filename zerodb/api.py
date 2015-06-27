#!/usr/bin/env python

import imp
import jsonpickle
import transaction
import zerodb
from flask import Flask, jsonify, session, request
from zerodb.catalog.query import optimize
from zerodb.catalog import query_json as qj

try:
    import simplejson as json
except:
    import json

PORT = 2015
HOST = "127.0.0.1"
DEBUG = True
DEV_SECRET_KEY = "development key"

app = Flask(__name__)
dbs = {}
models = None


@app.route("/_connect", methods=["GET", "POST"])
def connnect():
    if request.method == "GET":
        req = request.args
    elif request.method == "POST":
        req = request.form
    else:
        return jsonify(ok=0)

    username = req.get("username")
    passphrase = req.get("passphrase")
    host = req.get("host")
    port = req.get("port")
    if host and port:
        socket = (host, port)
    elif host:
        socket = host
    else:
        socket = None

    if not (username and passphrase and socket):
        return jsonify(ok=0, message="Incomplete login information")

    try:
        db = zerodb.DB(socket, username=username, password=passphrase)
    except Exception, e:
        return jsonify(ok=0, message=str(e), error_type=e.__class__.__name__)

    session["username"] = username
    dbs[username] = db

    return jsonify(ok=1)


@app.route("/<table_name>/_find")
def find(table_name):
    db = dbs[session["username"]]
    model = getattr(models, table_name)

    if request.method == "GET":
        req = request.args
    elif request.method == "POST":
        req = request.form
    else:
        return jsonify(ok=0)

    criteria = optimize(qj.compile(json.loads(req.get("criteria"))))

    skip = req.get("skip")
    if skip:
        skip = int(skip)
    limit = req.get("limit")
    if limit:
        limit = int(limit)

    result = db[model].query(criteria, skip=skip, limit=limit)

    return jsonpickle.encode(result, unpicklable=False)


@app.route("/<table_name>/_insert")
def insert(table_name):
    # POST has array of documents or one document
    db = dbs[session["username"]]
    model = getattr(models, table_name)

    if request.method == "POST":
        try:
            data = json.loads(request.form.get("data"))
            if isinstance(data, dict):
                data = [data]
            objs = [model(**row) for row in data]
            with transaction.manager:
                oids = [{"$oid": db.add(o)} for o in objs]
            return jsonify(status={"ok": 1}, oids=oids)
        except Exception, e:
            return jsonify(ok=0, message=str(e), error_type=e.__class__.__name__)
    else:
        return jsonify(ok=0)


@app.route("/_disconnect")
def disconnect():
    if "username" in session:
        username = session.pop("username")
        if username in dbs:
            del dbs[username]
    return jsonify(ok=1)


def run(data_models=None, host=HOST, port=PORT, debug=DEBUG, secret_key=DEV_SECRET_KEY):
    global models

    if isinstance(data_models, basestring):
        models = imp.load_source("models", data_models)
    else:
        models = data_models

    app.config["SECRET_KEY"] = secret_key
    print "XXX HERE", host, port
    app.run(host=host, port=port, debug=debug)


if __name__ == "__main__":
    run()
