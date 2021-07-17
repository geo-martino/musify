import json
import os
from os.path import join, exists
from urllib.parse import urlparse
from webbrowser import open as webopen

import requests


class Authorise:

    def __init__(self):

        # scopes of Spotify api access required by the functions in this program
        self.scopes = ['playlist-modify-public', 'playlist-modify-private', 'playlist-read-collaborative']

        # store token and headers
        self.TOKEN = None
        self.headers = None

    def auth(self, kind='user', scopes=None, force=False, lines=True, verbose=True):
        """
        Main method for authentication, tests/refreshes/reauthorises as needed
        
        :param kind: str, default='user'. 'user' or 'basic' authorisation.
        :param scopes: list, default=None. List of scopes to authorise for user. If None, uses defaults.
        :param force: bool, default=False. Ignore stored token and reauthorise new user or basic access token.
        :param lines: bool, default=True. Print lines around verbose.
        :param verbose: bool, default=True. Print extra information on function running.
        :return: dict. Headers for requests authorisation.
        """
        if verbose and lines:  # page break
            print('\n', '-' * 88, '\n', sep='')

        # load stored token
        if not self.TOKEN:
            self.TOKEN = self.load_spotify_token(verbose)

        # if no token, re-authorise and generate new tokens
        if not self.TOKEN or (scopes and scopes != self.scopes) or force:
            if kind == 'user':
                self.TOKEN = self.get_token_user(scopes)
            else:
                self.TOKEN = self.get_token_basic()

        # formatted as per spotify documentation
        self.headers = {'Authorization': f"{self.TOKEN['token_type']} {self.TOKEN['access_token']}"}

        # if call to user profile returns error, refresh token
        if kind == 'user' and 'error' in requests.get(f'{self.BASE_API}/me', headers=self.headers).json():
            self.TOKEN = self.refresh_token()
            self.headers = {'Authorization': f"{self.TOKEN['token_type']} {self.TOKEN['access_token']}"}
        elif 'error' in requests.get(f'{self.BASE_API}/markets', headers=self.headers).json():
            self.TOKEN = self.refresh_token()
            self.headers = {'Authorization': f"{self.TOKEN['token_type']} {self.TOKEN['access_token']}"}

        self.save_spotify_token()

        if verbose and lines:
            print('\n', '-' * 88, '\n', sep='')

        return self.headers

    def refresh_token(self, verbose=True):
        """
        Refreshes token once it has expired

        :param verbose: bool, default=True. Print extra information on function running.
        :return: dict. Authorisation response.
        """
        if verbose:
            print('Refreshing access token...', end=' ', flush=True)

        # post request to spotify
        auth_response = requests.post(f'{self.BASE_AUTH}/api/token', {
            'grant_type': 'refresh_token',
            'refresh_token': self.TOKEN['refresh_token'],
            'client_id': self.CLIENT_ID,
            'client_secret': self.CLIENT_SECRET,
        }).json()

        # call sometimes returns new refresh token, append previous one if not
        if 'refresh_token' not in auth_response:
            auth_response['refresh_token'] = self.TOKEN['refresh_token']

        if verbose:
            print('\33[92m', 'Done', '\33[0m', sep='')
        return auth_response

    def get_token_user(self, scopes=None, verbose=True):
        """
        Authenticates access to API with given user scopes
        
        :param scopes: list, default=None. List of scopes to authorise for user. If None, uses defaults.
        :param verbose: bool, default=True. Print extra information on function running.
        :return: dict. Authorisation response."""
        if verbose:
            print('Authorising user privilege access...')

        # get scopes for authentication
        if not scopes:
            scopes = self.scopes
        scopes = ' '.join(scopes)  # must be a list of space delimited strings

        params = {'client_id': os.environ['CLIENT_ID'],
                  'response_type': 'code',
                  'redirect_uri': 'http://localhost/',
                  'state': 'syncify',
                  'scope': scopes}

        # opens in user's browser to authenticate, user must wait for redirect and input the given link
        webopen(requests.post(f'{self.BASE_AUTH}/authorize', params=params).url)
        redirect_url = input('Authorise in new tab and input the returned url: ')

        # format out the access code from the returned url
        code = urlparse(redirect_url).query.split('&')[0].split('=')[1]

        # post request to spotify
        auth_response = requests.post(f'{self.BASE_AUTH}/api/token', {
            'grant_type': 'authorization_code',
            'code': code,
            'redirect_uri': 'http://localhost/',
            'client_id': self.CLIENT_ID,
            'client_secret': self.CLIENT_SECRET,
        }).json()

        if verbose:
            print('\33[92m', 'Done', '\33[0m', sep='')

        return auth_response

    def get_token_basic(self, verbose=True):
        """
        Authenticates for basic API access, no user authorisation required
        
        :param verbose: bool, default=True. Print extra information on function running.
        :return: dict. Authorisation response.
        """
        if verbose:
            print('Authorising basic API access...', end=' ', flush=True)

        # post request to spotify
        auth_response = requests.post(f'{self.BASE_AUTH}/api/token', {
            'grant_type': 'client_credentials',
            'client_id': self.CLIENT_ID,
            'client_secret': self.CLIENT_SECRET,
        }).json()

        if verbose:
            print('\33[92m', 'Done', '\33[0m', sep='')

        return auth_response

    def load_spotify_token(self, verbose=True):
        """
        Load stored spotify token from data folder
        
        :param verbose: bool, default=True. Print extra information on function running.
        :return: dict. Access token.
        """
        json_path = join(self.DATA_PATH, 'token.json')
        if not exists(json_path):
            return None

        if verbose:
            print('Saved access token found and imported.')

        with open(json_path, 'r') as file:  # load token
            token = json.load(file)

        return token

    def save_spotify_token(self):
        """Save new/updated token"""
        json_path = join(self.DATA_PATH, 'token.json')
        with open(json_path, 'w') as file:
            json.dump(self.TOKEN, file, indent=2)
