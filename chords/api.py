import os.path
import json

from flask import request, Response, url_for, send_from_directory
from werkzeug.utils import secure_filename
from jsonschema import validate, ValidationError

import models
import decorators
import analysis
from chords import app
from database import session
from utils import upload_path

post_schema = {
    "type": "object",
    "properties": {
        "file":
        {
            "type": "object",
            "properties": {
                "id": {"type": "number"}
            },
            "required": ["id"]
        }
    },
    "required": ["file"]
}

@app.route("/api/songs", methods=["GET"])
@decorators.accept("application/json")
def songs_get():
    """ Get a list of songs """

    # Get songs from database
    songs = session.query(models.Song).all()

    # Convert songs to JSON and return response
    data = json.dumps([song.as_dictionary() for song in songs])
    return Response(data, 200, mimetype="application/json")

@app.route("/api/songs", methods=["POST"])
@decorators.accept("application/json")
@decorators.require("application/json")
def songs_post():
    """ Post a new song to database """

    data = request.json

    # Check for valid JSON. If not available, return 422, Unprocessable Entity
    try:
        validate(data, post_schema)
    except ValidationError as error:
        data = json.dumps({"message": error.message})
        return Response(data, 422, mimetype="application/json")

    file_id = data["file"]["id"]
    song_file = session.query(models.File).get(file_id)

    if not song_file: # File with id = file_id is not in database
        message = "Could not find song file with file id {}".format(file_id)
        data = json.dumps({"message": message})
        return Response(data, 404, mimetype="application/json")
        
    song = models.Song(file_id=file_id)
    session.add(song)
    session.commit()
    data = json.dumps(song.as_dictionary())
    return Response(data, 201, mimetype="application/json")

@app.route("/uploads/<filename>", methods=["GET"])
def uploaded_file(filename):
    return send_from_directory(upload_path(), filename)

@app.route("/api/files", methods=["POST"])
@decorators.require("multipart/form-data")
@decorators.accept("application/json")
def file_post():
    file = request.files.get("file")
    if not file:
        data = {"message": "Could not find file data"}
        return Response(json.dumps(data), 422, mimetype="application/json")

    filename = secure_filename(file.filename)
    db_file = models.File(filename=filename)
    session.add(db_file)
    session.commit()
    file.save(upload_path(filename))

    data = db_file.as_dictionary()
    return Response(json.dumps(data), 201, mimetype="application/json")
