"""Main application and routing logic for Spotify Song Suggester."""
from os import getenv
from flask import Flask, request
from .models import DB
from spotipy import oauth2, Spotify


def create_app():
    """Create and configure an instance of the Flask application."""
    app = Flask(__name__)

    # Spotify API authentication
    cid = getenv('SPOTIFY_CLIENT_ID')
    secret = getenv('SPOTIFY_CLIENT_SECRET')

    credentials = oauth2.SpotifyClientCredentials(
        client_id=cid,
        client_secret=secret
    )

    # Add config for database
    app.config['SQLALCHEMY_DATABASE_URI'] = getenv('DATABASE_URL')
    DB.init_app(app)

    # Stop tracking modifications on SQLAlchemy config
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    @app.route('/')
    def root():
        """Base view of the app."""
        return 'Spotify Song Suggester Data Science Backend'

    @app.route('/track_info')
    def track_info():
        token = credentials.get_access_token()
        spotify = Spotify(auth=token)
        track_id = request.args.get('track',
                                    default='4uLU6hMCjMI75M1A2tKUQC',
                                    type=str)
        results = spotify.track(track_id)
        return results

    return app
