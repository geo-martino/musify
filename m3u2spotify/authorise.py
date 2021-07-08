import json
import os
import requests
from webbrowser import open as webopen
from urllib.parse import urlparse
from os.path import join, dirname, exists
from dotenv import load_dotenv

class Authorise:
    
    def __init__(self, base_api='https://api.spotify.com/v1', env_name='.env', verbose=True):
        self.verbose = verbose
        
        ENV_PATH = join(dirname(dirname(__file__)), env_name)
        load_dotenv(ENV_PATH)
        
        self.DATA_PATH = join(dirname(dirname(__file__)), 'data')
        if not exists(self.DATA_PATH):
            os.makedirs(self.DATA_PATH)

        self.CLIENT_ID = os.environ['CLIENT_ID']
        self.CLIENT_SECRET = os.environ['CLIENT_SECRET']
        
        self.BASE_API = base_api
        self.BASE_AUTH = 'https://accounts.spotify.com'  # base URL of all Spotify authorisation
        
        if self.verbose:
            print('\n', '-' * 88, '\n', sep='')
        self.token = self.load_spotify_token()
        
    def auth(self, kind='user'):
        if not self.token:
            if kind == 'user':
                self.token = self.get_token_user()
            else:
                self.token = self.get_token_basic()
        
        headers = self.get_headers()
        self.save_spotify_token()
        
        if self.verbose:
            print('\n', '-' * 88, '\n', sep='')
        
        return headers
    
    def get_headers(self):
        if not self.token:
            return

        headers = {'Authorization': f"{self.token['token_type']} {self.token['access_token']}"}

        if 'error' in requests.get(f'{self.BASE_API}/me', headers=headers).json():
            self.token = self.refresh_token()
            headers = {'Authorization': f"{self.token['token_type']} {self.token['access_token']}"}

        return headers
    
    def refresh_token(self):
        if self.verbose:
            print('Refreshing access token...', end=' ', flush=True)
        
        auth_response = requests.post(f'{self.BASE_AUTH}/api/token', {
            'grant_type': 'refresh_token',
            'refresh_token': self.token['refresh_token'],
            'client_id': self.CLIENT_ID,
            'client_secret': self.CLIENT_SECRET,
        }).json()

        if 'refresh_token' not in auth_response:
            auth_response['refresh_token'] = self.token['refresh_token']


        if self.verbose:
            print('\33[92m', 'Done', '\33[0m', sep='')
        return auth_response

    def get_token_user(self):
        if self.verbose:
            print('Authorising user privilege access...')
        
        params = {'client_id': os.environ['CLIENT_ID'],
                  'response_type': 'code',
                  'redirect_uri': 'http://localhost/',
                  'state': 'm3u2spotify',
                  'scope': 'playlist-modify-public playlist-modify-private'}

        webopen(requests.post(self.USERAUTH_URL, params=params).url)
        redirect_url = input('Authorise in new tab and input the returned url: ')
        code = urlparse(redirect_url).query.split('&')[0].split('=')[1]

        auth_response = requests.post(f'{self.BASE_AUTH}/authorize', {
            'grant_type': 'authorization_code',
            'code': code,
            'redirect_uri': 'http://localhost/',
            'client_id': self.CLIENT_ID,
            'client_secret': self.CLIENT_SECRET,
        }).json()

        if self.verbose:
            print('\33[92m', 'Done', '\33[0m', sep='')

        return auth_response

    def get_token_basic(self):
        if self.verbose:
            print('Authorising basic API access...', end=' ', flush=True)
        
        auth_response = requests.post(f'{self.BASE_AUTH}/authorize', {
            'grant_type': 'client_credentials',
            'client_id': self.CLIENT_ID,
            'client_secret': self.CLIENT_SECRET,
        }).json()

        if self.verbose:
            print('\33[92m', 'Done', '\33[0m', sep='')
        
        return auth_response
    
    def load_spotify_token(self):
        json_path = join(self.DATA_PATH, 'token.json')
        if not exists(json_path):
            return None

        if self.verbose:
            print('Access token found. Loading stored access token.')
        
        with open(json_path, 'r') as file:
            token = json.load(file)
        
        return token

    def save_spotify_token(self):
        json_path = join(self.DATA_PATH, 'token.json')
        with open(json_path, 'w') as file:
            json.dump(self.token, file, indent=2)
        
    