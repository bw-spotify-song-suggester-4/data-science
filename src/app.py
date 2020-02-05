"""Main application and routing logic for Spotify Song Suggester."""
from flask_sqlalchemy import SQLAlchemy
from flask import Flask, request
import json
import numpy as np
from os import getenv
import pickle
from spotipy import oauth2, Spotify


def create_app():
    """Create and configure an instance of the Flask application."""
    app = Flask(__name__)

    # Add config for database
    pg_user = getenv('POSTGRES_USER')
    pg_pw = getenv('POSTGRES_PASSWORD')
    pg_url = getenv('POSTGRES_URL')
    pg_db = getenv('POSTGRES_DB')
    DATABASE_URL = f'postgresql+psycopg2://{pg_user}:{pg_pw}@{pg_url}/{pg_db}'
    app.config['SQLALCHEMY_DATABASE_URI'] = DATABASE_URL

    # Stop tracking modifications on SQLAlchemy config
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    DB = SQLAlchemy(app)
    DB.Model.metadata.reflect(DB.engine)

    # Spotify API authentication
    cid = getenv('SPOTIFY_CLIENT_ID')
    secret = getenv('SPOTIFY_CLIENT_SECRET')

    credentials = oauth2.SpotifyClientCredentials(
        client_id=cid,
        client_secret=secret
    )

    pickle_model = pickle.load(open('./rm_04.pkl', 'rb'))

    @app.route('/')
    def root():
        """Base view of the app."""
        return 'Spotify Song Suggester Data Science Backend'

    @app.route('/track-info')
    def track_info():
        token = credentials.get_access_token()
        spotify = Spotify(auth=token)
        track_id = request.args.get(
            'track_id', default='06w9JimcZu16KyO3WXR459', type=str
        )
        results = spotify.track(track_id)
        return results

    @app.route('/audio-features')
    def audio_features():
        token = credentials.get_access_token()
        spotify = Spotify(auth=token)
        track_id = request.args.get(
            'track_id', default='06w9JimcZu16KyO3WXR459', type=str
        )
        results = spotify.audio_features(track_id)
        return json.dumps(results)

    @app.route('/get-suggestions')
    def get_suggestions():
        seed_track = request.args.get(
            'seed', default='06w9JimcZu16KyO3WXR459', type=str
        )
        num_tracks = request.args.get(
            'num', default=10, type=int
        )
        query1 = Track.query.filter(Track.track_id == seed_track).first()
        _, ind = pickle_model.query(
            query1.to_array().reshape(1, -1), k=num_tracks+1
        )
        suggested_tracks = [id.item() for id in ind[0]]
        query2 = Track.query.filter(Track.id.in_(suggested_tracks))
        query2 = query2.filter(Track.track_id != seed_track).all()

        return f'{{"seed": {query1}, "results": {query2}}}'

    class Track(DB.Model):
        __table__ = DB.Model.metadata.tables['track']

        def to_array(self):
            return np.array([self.acousticness,
                            self.danceability,
                            self.energy,
                            self.instrumentalness,
                            self.key,
                            self.liveness,
                            self.loudness,
                            self.mode,
                            self.speechiness,
                            self.tempo,
                            self.time_signature,
                            self.valence])

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

    return app
