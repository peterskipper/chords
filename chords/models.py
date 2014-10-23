import os.path

from flask import url_for
from sqlalchemy import Column, Integer, String, Sequence, ForeignKey
from sqlalchemy.orm import relationship

from chords import app
from database import Base, engine

class File(Base):
    """
    Domain model for a song file
    """
    __tablename__ = "file"

    #database fields
    id = Column(Integer, Sequence("file_id_sequence"), primary_key=True)
    filename = Column(String(128), nullable=False)
    song = relationship("Song", uselist=False, backref="file")

    def as_dictionary(self):
        return {"id": self.id, 
            "name": self.filename,
            "path": url_for("uploaded_file", filename=self.filename)
            }


class Song(Base):
    """
    Domain model for a song
    """
    __tablename__ = "song"

    # database fields
    id = Column(Integer, Sequence("song_id_sequence"), primary_key=True)
    file_id = Column(Integer, ForeignKey("file.id"))

    def as_dictionary(self):
        return {"id": self.id, "file": {"id": self.file.id, "name": self.file.filename}}
