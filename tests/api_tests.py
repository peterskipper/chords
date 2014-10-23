import unittest
import os
import shutil
import json
from urlparse import urlparse
from StringIO import StringIO

# Configure our app to use the testing databse
os.environ["CONFIG_PATH"] = "chords.config.TestingConfig"

from chords import app
from chords import models
from chords.utils import upload_path
from chords.database import Base, engine, session

class TestAPI(unittest.TestCase):
    """ Tests for the chords API """

    def setUp(self):
        """ Test setup """
        self.client = app.test_client()

        # Set up the tables in the database
        Base.metadata.create_all(engine)

        # Create folder for test uploads
        os.mkdir(upload_path())

    def testGetEmptySongs(self):
        """ Query Empty Song List """
        response = self.client.get("/songs",
            headers=[("Accept", "application/json")]
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.mimetype, "application/json")

        data = json.loads(response.data)
        self.assertEqual(data, [])

    def testGetSongs(self):
        """ Query Song List """

        # Add files and songs to db
        file1 = models.File(filename="SongFile 1")
        file2 = models.File(filename="SongFile 2")
        session.add_all([file1, file2])
        session.commit()
        song1 = models.Song(file_id=file1.id)
        song2 = models.Song(file_id=file2.id)
        session.add_all([song1, song2])
        session.commit()

        response = self.client.get("/songs",
            headers=[("Accept","application/json")]
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.mimetype, "application/json")

        songs = json.loads(response.data)
        self.assertEqual(len(songs), 2)

        song1 = songs[0]
        self.assertEqual(song1["id"], 1)
        self.assertEqual(song1["file"]["id"], 1)
        self.assertEqual(song1["file"]["name"], "SongFile 1")

        song2 = songs[1]
        self.assertEqual(song2["id"], 2)
        self.assertEqual(song2["file"]["id"], 2)
        self.assertEqual(song2["file"]["name"], "SongFile 2")

    def testUnsupportedAcceptHeader(self):
        response = self.client.get("/songs",
            headers=[("Accept", "application/xml")]
            )

        self.assertEqual(response.status_code, 406)
        self.assertEqual(response.mimetype, "application/json")

        data = json.loads(response.data)
        self.assertEqual(data["message"],
            "Request must accept application/json data")

    def testPostSong(self):
        """ Posting a new Song to db """
        
        # Add a new file to db
        file1 = models.File(filename="Happy Birthday")
        session.add(file1)
        session.commit()

        # Add a new song via endpoint
        song = {
            "file": {
            "id": 1
            }
        }

        response = self.client.post("/songs",
            data=json.dumps(song),
            content_type="application/json",
            headers=[("Accept", "application/json")]
            )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.mimetype, "application/json")

        # Check response data 
        data = json.loads(response.data)
        self.assertEqual(data["id"], 1)
        self.assertEqual(data["file"]["id"], 1)
        self.assertEqual(data["file"]["name"], "Happy Birthday")

        # Check db
        songs = session.query(models.Song).all()
        self.assertEqual(len(songs), 1)

        song = songs[0]
        self.assertEqual(song.file_id, file1.id)
        self.assertEqual(song.file.filename, "Happy Birthday")
        self.assertEqual(song.file.id, 1)

    def testPostNonExistentSong(self):
        """ Post A Song With No File """
        song = {
            "file": {
            "id": 1
            }
        }

        response = self.client.post("/songs",
            data=json.dumps(song),
            content_type="application/json",
            headers=[("Accept", "application/json")]
            )

        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.mimetype, "application/json")

        data = response.data
        data = json.loads(data)
        self.assertEqual(data["message"], "Could not find song file with file id 1")


    def testUnsupportedMimetype(self):
        data = "<xml></xml>"
        response = self.client.post("/songs",
            data = json.dumps(data),
            content_type="application/xml",
            headers=[("Accept", "application/json")]
            )

        self.assertEqual(response.status_code, 415)
        self.assertEqual(response.mimetype, "application/json")

        data = json.loads(response.data)
        self.assertEqual(data["message"], 
            "Request must contain application/json data")

    def testMissingData(self):
        """ Posting a post with a missing body """
        song = {
            "file": {}
        }

        response = self.client.post("/songs",
            data=json.dumps(song),
            content_type="application/json",
            headers=[("Accept", "application/json")]
            )

        self.assertEqual(response.status_code, 422)
        data = json.loads(response.data)
        self.assertEqual(data["message"], "'id' is a required property")

    def testInvalidData(self):
        """ Posting a post with an invalid body """
        song = {
            "file": {
            "id": "not_an_id"
            }
        }

        response = self.client.post("/songs",
            data=json.dumps(song),
            content_type="application/json",
            headers=[("Accept", "application/json")]
            )

        self.assertEqual(response.status_code, 422)
        
        data = json.loads(response.data)
        self.assertEqual(data["message"], "u'not_an_id' is not of type 'number'")

    def testGetUploadedFile(self):
        """ Grab an uploaded file """
        path = upload_path("test.txt")
        with open(path, "w") as f:
            f.write("File contents")

        response = self.client.get("/uploads/test.txt")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.mimetype, "text/plain")
        self.assertEqual(response.data, "File contents")

    def testFileUpload(self):
        """ Upload a file to server """
        data = {
            "file": (StringIO("File contents"), "test.txt")
        }

        response = self.client.post("/api/files",
            data=data,
            content_type="multipart/form-data",
            headers=[("Accept", "application/json")]
            )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.mimetype, "application/json")

        data = json.loads(response.data)
        self.assertEqual(urlparse(data["path"]).path, "/uploads/test.txt")

        path = upload_path("test.txt")
        self.assertTrue(os.path.isfile(path))
        with open(path) as f:
            contents = f.read()
        self.assertEqual(contents, "File contents")

    def tearDown(self):
        """ Test teardown """
        # Remove the tables and their data from the database
        Base.metadata.drop_all(engine)

        # Delete test upload folder
        shutil.rmtree(upload_path())

