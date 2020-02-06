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
    app.config['SQLALCHEMY_DATABASE_URI'] = getenv('DATABASE_URL')

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

    model = pickle.load(open('./rm_05.pkl', 'rb'))
    scaler = pickle.load(open('./sc_05.pkl', 'rb'))

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
        _, results = model.query(
            scaler.transform([query1.to_array()]), k=num_tracks+1
        )
        suggested_tracks = [id.item() for id in results[0]]
        stmt = Track.query.filter(Track.id.in_(suggested_tracks))
        query2 = stmt.filter(Track.track_id != seed_track).all()

        return f'{{"seed": {query1}, "results": {query2}}}'

    @app.route('/search')
    def search():
        default_track = 'Perfect Nelson Remix'
        track_name = request.args.get(
            'track_name', default=default_track, type=str
        )
        limit = request.args.get(
            'limit', default=6, type=int
        )
        page = request.args.get(
            'page', default=0, type=int
        )
        token = credentials.get_access_token()
        spotify = Spotify(auth=token)
        results = spotify.search(
            q=f'track:{track_name}',
            type='track',
            limit=limit,
            offset=limit*page
        )
        return get_search_info(results)

    def get_search_info(results):
        try:
            output = []
            for item in results['tracks']['items']:
                info_dict = dict()
                info_dict['artist_name'] = item['artists'][0]['name']
                info_dict['track_name'] = item['name']
                info_dict['track_id'] = item['id']
                info_dict['cover_art'] = item['album']['images'][1]['url']
                output.append(info_dict)
            return json.dumps(output)
        except Exception as e:
            return f'Error while parsing the results: {e}'

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
                'artist_name': self.artist_name
            }

        def __repr__(self):
            return json.dumps(self.print_dict())

    return app
