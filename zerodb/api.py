#!/usr/bin/env python

# Warning!
# At the moment, this API is safe to use only on same machine
# (no https etc)

import imp
import jsonpickle
import six
import transaction
import zerodb
from flask import Flask, jsonify, session, request
from flask.ext.cors import CORS
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
cors = CORS(app, supports_credentials=True)
dbs = {}
models = None
zeosocket = None


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
    if zeosocket:
        socket = zeosocket
    else:
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
    except Exception as e:
        return jsonify(ok=0, message=str(e), error_type=e.__class__.__name__)

    session["username"] = username
    dbs[username] = db

    return jsonify(ok=1)


@app.route("/<table_name>/_find", methods=["GET", "POST"])
def find(table_name):
    db = dbs[session["username"]]
    model = getattr(models, table_name)

    if request.method == "GET":
        req = request.args
    elif request.method == "POST":
        req = request.form
    else:
        return jsonify(ok=0)

    if req.get("criteria") is None:
        criteria = json.loads(request.data).get("criteria")
    else:
        criteria = json.loads(req.get("criteria"))

    if isinstance(criteria, dict) and (len(criteria) == 1) and "_id" in criteria:
        ids = [c["$oid"] for c in criteria["_id"]]
    else:
        ids = None
        criteria = optimize(qj.compile(criteria))

    skip = req.get("skip")
    if skip:
        skip = int(skip)

    limit = req.get("limit")
    if limit:
        limit = int(limit)

    sort = req.get("sort")
    if sort:
        try:
            sort = json.loads(sort)
        except ValueError:
            if sort.startswith("-"):
                sort_index = sort[1:].strip()
                reverse = True
            else:
                sort_index = sort
                reverse = None
        if isinstance(sort, dict):
            assert len(sort) == 1  # Only one field at the moment
            sort_index, direction = sort.popitem()
            reverse = (direction >= 0)
        elif isinstance(sort, list):
            sort_index = sort[0]
            reverse = None
    else:
        sort_index = None
        reverse = None

    if ids:
        skip = skip or 0
        end = skip + limit if limit else None
        ids = ids[skip:end]
        result = db[model][ids]
    else:
        result = db[model].query(criteria, skip=skip, limit=limit, sort_index=sort_index, reverse=reverse)

    return jsonpickle.encode(list(result), unpicklable=False)


@app.route("/<table_name>/_remove", methods=["GET", "POST"])
def remove(table_name):
    db = dbs[session["username"]]
    model = getattr(models, table_name)

    if request.method == "GET":
        req = request.args
    elif request.method == "POST":
        req = request.form
    else:
        return jsonify(ok=0)

    criteria = req.get("criteria")
    ids = req.get("_id")
    if criteria:
        criteria = json.loads(req.get("criteria"))
        if isinstance(criteria, dict) and (len(criteria) == 1) and "_id" in criteria:
            ids = [c["$oid"] for c in criteria["_id"]]
        else:
            ids = None
            criteria = optimize(qj.compile(criteria))
        result = db[model].query(criteria)
    elif ids:
        ids = json.loads(ids)
        result = db[model][ids]
    else:
        return jsonify(ok=0)

    try:
        with transaction.manager:
            count = db.remove(result)
    except Exception as e:
        return jsonify(ok=0, message=str(e), error_type=e.__class__.__name__)

    return jsonify(ok=1, count=count)


@app.route("/<table_name>/_insert", methods=["GET", "POST"])
def insert(table_name):
    # POST has array of documents or one document
    db = dbs[session["username"]]
    model = getattr(models, table_name)

    if request.method == "POST":
        try:
            if request.form.get("docs") is None:
                data = json.loads(request.data).get("docs")
            else:
                data = json.loads(request.form.get("docs"))
            if isinstance(data, dict):
                data = [data]
            objs = [model(**row) for row in data]
            with transaction.manager:
                oids = [{"$oid": db.add(o)} for o in objs]
            return jsonify(status={"ok": 1}, oids=oids)
        except Exception as e:
            return jsonify(ok=0, message=str(e), error_type=e.__class__.__name__)
    else:
        return jsonify(ok=0)


@app.route("/<table_name>/_get", methods=["GET", "POST"])
def get(table_name):
    db = dbs[session["username"]]
    model = getattr(models, table_name)

    if request.method == "GET":
        req = request.args
    elif request.method == "POST":
        req = request.form
    else:
        return jsonify(ok=0)

    data = json.loads(req["_id"])

    return jsonpickle.encode(db[model][data], unpicklable=False)


@app.route("/_disconnect", methods=["GET", "POST"])
def disconnect():
    if "username" in session:
        username = session.pop("username")
        if username in dbs:
            del dbs[username]
    return jsonify(ok=1)


def run(data_models=None, host=HOST, port=PORT, debug=DEBUG, secret_key=DEV_SECRET_KEY, zeo_socket=None, **kw):
    global models
    global zeosocket

    if isinstance(data_models, six.string_types):
        models = imp.load_source("models", data_models)
    else:
        models = data_models

    zeosocket = zeo_socket

    app.config["SECRET_KEY"] = secret_key
    app.run(host=host, port=port, debug=debug, **kw)


if __name__ == "__main__":
    run()
