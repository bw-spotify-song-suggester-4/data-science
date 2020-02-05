"""Main application and routing logic for Spotify Song Suggester."""
from flask_sqlalchemy import SQLAlchemy
from flask import Flask, request
import json
from os import getenv
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

    @app.route('/')
    def root():
        """Base view of the app."""
        return 'Spotify Song Suggester Data Science Backend'

    @app.route('/track-info')
    def track_info():
        token = credentials.get_access_token()
        spotify = Spotify(auth=token)
        track_id = request.args.get('track_id',
                                    default='4uLU6hMCjMI75M1A2tKUQC',
                                    type=str)
        results = spotify.track(track_id)
        return results

    @app.route('/audio-features')
    def audio_features():
        token = credentials.get_access_token()
        spotify = Spotify(auth=token)
        track_id = request.args.get('track_id',
                                    default='4uLU6hMCjMI75M1A2tKUQC',
                                    type=str)
        results = spotify.audio_features(track_id)
        return json.dumps(results)

    return app
