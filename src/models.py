from flask_sqlalchemy import SQLAlchemy
import json
DB = SQLAlchemy()

DB.Model.metadata.reflect(DB.engine)


class Track(DB.Model):
    __table__ = DB.Model.metadata.tables['track']

    def print_dict(self):
        return {
            'track_id': self.track_id,
            'track_name': self.track_name,
            'artist_name': self.artist_name,
            'acousticness': self.acousticness,
            'danceability': self.danceability,
            'duration_ms': self.duration_ms,
            'energy': self.energy,
            'instrumentalness': self.instrumentalness,
            'key': self.key,
            'liveness': self.liveness,
            'loudness': self.loudness,
            'mode': self.mode,
            'speechiness': self.speechiness,
            'tempo': self.tempo,
            'time_signature': self.time_signature,
            'valence': self.valence,
            'popularity': self.popularity
        }

    def __repr__(self):
        return json.dumps(self.print_dict())
