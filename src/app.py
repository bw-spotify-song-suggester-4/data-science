"""Main application and routing logic for Spotify Song Suggester."""
import base64
from flask_sqlalchemy import SQLAlchemy
from flask import Flask, request
import io
import json
import matplotlib.pyplot as plt
import numpy as np
from os import getenv
import pandas as pd
import pickle
from spotipy import oauth2, Spotify


def create_app():
    """Create and configure an instance of the Flask application

    Returns
    -------
    app : Flask object
        The instance of the Flask application.

    """
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

    # KDTree model and data scaler loaded from pickle
    model = pickle.load(open('./rm_05.pkl', 'rb'))
    scaler = pickle.load(open('./sc_05.pkl', 'rb'))

    @app.route('/')
    def root():
        """Base view of the app

        Returns
        -------
        str
            a "hello world" style string to show the site is working
        """

        return 'Spotify Song Suggester Data Science Backend'

    @app.route('/track-info')
    def track_info():
        """Get the information for a Spotify track

        This function takes a request with a given track ID and returns a JSON
        object with the artist name, track name, track ID, and album art

        Returns
        -------
        json
            a json of the track info to send to the back-end
        """

        token = credentials.get_access_token()
        spotify = Spotify(auth=token)
        track_id = request.args.get(
            'track_id', default='06w9JimcZu16KyO3WXR459', type=str
        )
        results = spotify.track(track_id)
        return parse_track_info(results)

    @app.route('/audio-features')
    def audio_features():
        """Get the audio features for a Spotify track

        This function takes a request with a given track ID and returns a JSON
        object with the audio features and track identification

        Returns
        -------
        json
            a json of the audio features and track identification to send to
            the back-end
        """

        token = credentials.get_access_token()
        spotify = Spotify(auth=token)
        track_id = request.args.get(
            'track_id', default='06w9JimcZu16KyO3WXR459', type=str
        )
        results = spotify.audio_features(track_id)
        return json.dumps(results)

    @app.route('/get-suggestions')
    def get_suggestions():
        """Get the model suggestions for similar tracks for a Spotify track

        This function takes a request with a seed track ID and the number of
        tracks to return. Returns a JSON object with track information for the
        seed and resulting suggested tracks

        Returns
        -------
        json
            a json of the information for seed track and similar track
            suggestions to send to the back-end
        """

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
        """Get the search results from a Spotify search by track title

        This function takes a request with a searched track name, the number
        of song results to return for each page, and the number of the page
        of results to display (indexed from 1). Returns a JSON object of the
        results of the title search with the following information:

            artist name, track name, track ID, album art

        Returns
        -------
        json
            a json of the search results information to send to the back-end
        """

        default_track = 'Perfect Nelson Remix'
        track_name = request.args.get(
            'track_name', default=default_track, type=str
        )
        limit = request.args.get(
            'limit', default=6, type=int
        )
        page = request.args.get(
            'page', default=1, type=int
        )
        token = credentials.get_access_token()
        spotify = Spotify(auth=token)
        results = spotify.search(
            q=f'track:{track_name}',
            type='track',
            limit=limit,
            offset=limit*(page-1)
        )
        return get_search_info(results)

    @app.route('/match-feature')
    def match_feature():
        """Get the top/bottom songs that match a range of the audio feature

        This function takes a request with a target feature, minimum and
        maximum of that feature, and the maximum number of songs to display

        Returns
        -------
        str
            a string representing the database query results for tracks that
            match the specified range of the target feature
        """

        feature = request.args.get(
            'feature', default='energy', type=str
        )
        min_ = request.args.get(
            'min', type=float
        )
        max_ = request.args.get(
            'max', type=float
        )
        lim = request.args.get(
            'limit', default=20, type=int
        )

        output = {}
        condition1 = f'(Track.{feature} >= min_)'
        condition2 = f'(Track.{feature} <= max_)'
        if min_ and max_:
            condition = f'({condition1} & {condition2})'
            output = Track.query.filter(eval(condition)).limit(lim).all()
        elif min_:
            output = Track.query.filter(eval(condition1)).limit(lim).all()
        elif max_:
            output = Track.query.filter(eval(condition2)).limit(lim).all()

        return str(output)

    @app.route('/visualize')
    def visualize():
        """Plot six audio features for two given song IDs

        This function takes a request for two song IDs and two labels for
        those IDs to display on the chart. The chosen audio features to
        display are:

            acousticness, danceability, energy,
            instrumentalness, liveness, valence

        The values are plotted on a radar chart and were chosen because they
        all range from 0 to 1. Only tracks in the AWS database can currently
        be searched, but extra work could be done to take in any track ID.

        Returns
        -------
        png
            a png image file of the radar chart for the given IDs and labels
        """
        plt.switch_backend('Agg')  # avoid error from matplotlib

        id_a = request.args.get(
            'id_a', default='06w9JimcZu16KyO3WXR459', type=str
        )
        id_b = request.args.get(
            'id_b', default='6XzyAQs2jU4PMWmnFlEQLW', type=str
        )
        label_a = request.args.get(
            'label_a', default=id_a, type=str
        )
        label_b = request.args.get(
            'label_b', default=id_b, type=str
        )

        track_a = Track.query.filter(Track.track_id == id_a).first()
        track_b = Track.query.filter(Track.track_id == id_b).first()

        track_df = pd.DataFrame(
            [
                track_a.to_dict(),
                track_b.to_dict()
            ]
        )

        if label_a == id_a:
            label_a = f"{track_df.loc[0]['track_name'][:30]}"

        if label_b == id_b:
            label_b = f"{track_df.loc[1]['track_name'][:30]}"

        vis_labels = [label_a, label_b]

        labels = [
            'acousticness',
            'danceability',
            'energy',
            'instrumentalness',
            'liveness',
            'valence'
        ]

        num_vals = len(labels)
        angles = [n / float(num_vals) * 2 * np.pi for n in range(num_vals)]
        angles += angles[:1]  # make cyclic to connect vertices in polygon

        # Set figure settings
        fig, ax = plt.subplots(figsize=(6, 6), subplot_kw=dict(polar=True))
        ax.set_theta_offset(np.pi / 2)
        ax.set_theta_direction(-1)
        ax.set_thetagrids(np.degrees(angles), labels)
        ax.set_rlabel_position(0)
        ax.set_yticks([0.20, 0.40, 0.60, 0.80])
        ax.set_yticklabels(['0.20', '0.40', '0.60', '0.80'])
        ax.set_ylim(0, 1)

        # Plot and fill the radar polygons
        feature_df = track_df[labels]
        colors = ['#EF019F', '#780150']
        for i, color in enumerate(colors):
            values = feature_df.loc[i].values.flatten().tolist()
            values += values[:1]  # make cyclic to connect vertices in polygon
            ax.plot(
                angles,
                values,
                color=color,
                linewidth=1,
                linestyle='solid',
                label=vis_labels[i]
            )
            ax.fill(angles, values, color=color, alpha=0.25)

            # Set feature labels so they don't overlap the chart
            for label, angle in zip(ax.get_xticklabels(), angles):
                if angle in [0, np.pi]:
                    label.set_horizontalalignment('center')
                elif 0 < angle < np.pi:
                    label.set_horizontalalignment('left')
                else:
                    label.set_horizontalalignment('right')
        ax.legend(loc='best')

        # Save the figure as an image to output on the app
        pic_bytes = io.BytesIO()
        plt.savefig(pic_bytes, format='png')
        pic_bytes.seek(0)
        data = base64.b64encode(pic_bytes.read()).decode('ascii')
        plt.clf()
        return f"<img src='data:image/png;base64,{data}'>"

    def get_search_info(results):
        """A helper function to output specific track information from search results

        Parameters
        ----------
        results : json
            The results from a Spotify search for a track title

        Returns
        -------
        json
            a json object with the selected track information for the search
            results to send to the back-end

        Raises
        ------
        Exception:
            an exception if there was an error retrieving the data
        """

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

    def parse_track_info(results):
        """A helper function to output specific track information

        Parameters
        ----------
        results : json
            The results from a Spotify API call for track information

        Returns
        -------
        json
            a json object with the selected track information to send to the
            back-end

        Raises
        ------
        Exception:
            an exception if there was an error retrieving the data
        """

        try:
            output = []
            info_dict = dict()
            info_dict['artist_name'] = results['artists'][0]['name']
            info_dict['track_name'] = results['name']
            info_dict['track_id'] = results['id']
            info_dict['cover_art'] = results['album']['images'][1]['url']
            output.append(info_dict)
            return json.dumps(output)
        except Exception as e:
            return f'Error while parsing the results: {e}'

    class Track(DB.Model):
        """A class used to represent a Spotify track

        Attributes
        ----------
        __table__ : table
            a reference to the table stored in the AWS database instance

        Methods
        -------
        to_array()
            Convert the data used as input for the KDTree model to an array

        to_dict()
            Convert track data and audio features to a dictionary for easy
            JSON output

        result_dict()
            Generate the basic track data the front-end needs to display

        __repr__()
            Display the basic track data in JSON format

        """
        __table__ = DB.Model.metadata.tables['track']

        def to_array(self):
            """Converts audio features used in the model to a NumPy array

            Returns
            -------
            array
                an array of the audio features used in the model
            """

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

        def to_dict(self):
            """Converts the information in the database to a dictionary

            This dictionary is mostly used for printing and display purposes,
            as well as getting a nice format to change the data back into a
            DataFrame.

            Returns
            -------
            dict
                a dict of the track features in the database
            """

            return {
                'track_id': self.track_id,
                'track_name': self.track_name,
                'artist_name': self.artist_name,
                'acousticness': self.acousticness,
                'danceability': self.danceability,
                'energy': self.energy,
                'instrumentalness': self.instrumentalness,
                'key': self.key,
                'liveness': self.liveness,
                'loudness': self.loudness,
                'mode': self.mode,
                'speechiness': self.speechiness,
                'tempo': self.tempo,
                'time_signature': self.time_signature,
                'valence': self.valence
            }

        def result_dict(self):
            """Converts track display information to a dict

            This dictionary is used for display purposes and for sending only
            the relevant track information to the back-end.

            Returns
            -------
            dict
                a dict with the relevant track display information
            """

            return {
                'track_id': self.track_id,
                'track_name': self.track_name,
                'artist_name': self.artist_name
            }

        def __repr__(self):
            """The default representation of a Track

            This is a JSON representation of the relevant track information.

            Returns
            -------
            json
                a json of the relevant track information to send to the
                back-end
            """

            return json.dumps(self.result_dict())

    return app
