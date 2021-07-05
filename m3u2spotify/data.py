import glob
import json
import os
import re
from os.path import basename, dirname, exists, join, splitext

import mutagen


class Data:

    def __init__(self):
        self.DATA_PATH = join(dirname(dirname(__file__)), 'data')
        if not exists(self.DATA_PATH):
            os.makedirs(self.DATA_PATH)

    def get_m3u_metadata(self, playlists_path):
        filepaths = glob.glob(join(playlists_path, '*.m3u'))
        playlists = {}

        print('Loading m3u playlists...', end='')

        for playlist_path in filepaths:
            playlist_name = splitext(basename(playlist_path))[0]

            with open(playlist_path, 'r', encoding='utf-8') as m3u:
                playlist_metadata = [self.get_song_metadata(i, songpath.rstrip()) for i, songpath in enumerate(m3u) if
                                     exists(songpath.rstrip())]
                playlists[playlist_name] = playlist_metadata

        print('\33[92m', 'Done', '\33[0m')

        print('Found the following playlists:')
        max_width = len(max(playlists.keys(), key=len))
        for name, playlist in sorted(playlists.items(), key=lambda x: x[0].lower()):
            length = str(len(playlist)) + ' tracks'
            print(f'{name : <{max_width}}', ':', '\33[92m', f'{length : >9} ', '\33[0m')

        return playlists

    @staticmethod
    def get_song_metadata(position, path):
        try:
            file_data = mutagen.File(path)
        except mutagen.MutagenError:
            print('\nERROR: Could not load', path, end='')
            return {}

        metadata = {'position': position}
        file_extension = splitext(path)[1].lower()
        filetype_tags = {
            '.flac': {'title': ['title'],
                      'artist': ['artist'],
                      'album': ['album'],
                      'track': ['tracknumber'],
                      'genre': ['genre'],
                      'year': ['year', 'date']},
            '.mp3': {'title': ['TIT2'],
                     'artist': ['TPE1', 'TPE2'],
                     'album': ['TALB'],
                     'track': ['TRCK'],
                     'genre': ['TCON'],
                     'year': ['TDRC', 'TYER', 'TDAT']},
            '.m4a': {'title': ['©nam'],
                     'artist': ['©ART', 'aART'],
                     'album': ['©alb'],
                     'track': ['trkn'],
                     'genre': ['©gen'],
                     'year': ['©day']},
            '.wma': {'title': ['Title'],
                     'artist': ['Author', 'WM/AlbumArtist'],
                     'album': ['WM/AlbumTitle'],
                     'track': ['WM/TrackNumber'],
                     'genre': ['WM/Genre'],
                     'year': ['WM/Year']}
        }

        for key, tags in filetype_tags.get(file_extension, {'': []}).items():
            for tag in tags:
                if file_extension == '.wma':
                    metadata[key] = file_data.get(tag, [mutagen.asf.ASFUnicodeAttribute(None)])[0].value
                elif file_extension == '.m4a' and key == 'track':
                    metadata[key] = file_data.get(tag, [None])[0][0]
                else:
                    metadata[key] = file_data.get(tag, [None])[0]

                if len(str(metadata[key]).strip()) == 0:
                    metadata[key] = None

                if metadata[key] is not None:
                    break

        if metadata.get('track', None) is not None and not isinstance(metadata.get('track', None), int):
            metadata['track'] = int(re.sub('[^0-9]', '', metadata['track']))

        try:
            metadata['year'] = int(re.sub('[^0-9]', '', metadata.get('year', ''))[:4])
        except (ValueError, TypeError):
            metadata['year'] = 0

        metadata['length'] = file_data.info.length
        return metadata

    def import_uri(self, playlists):
        json_path = join(self.DATA_PATH, 'uri.json')
        if not exists(json_path):
            return playlists

        print(f'Importing locally stored URIs...', end='')

        with open(json_path, 'r') as file:
            uri = json.load(file)

        for playlist in playlists.values():
            for song in playlist:
                album = uri.get(song.get('album', None), {})
                if song['title'] in album:
                    song['uri'] = album[song['title']]

        print('\33[92m', 'Done', '\33[0m')
        return playlists

    def export_uri(self, playlists):
        json_path = join(self.DATA_PATH, 'uri.json')
        if exists(json_path):
            with open(json_path, 'r') as file:
                uri = json.load(file)
        else:
            uri = {}

        print(f'Saving URIs locally...', end='')

        for playlist in playlists.values():
            for song in playlist:
                if 'uri' in song:
                    uri[song['album']] = uri.get(song['album'], {})
                    uri[song['album']][song['title']] = song['uri']

        uri = {k: v for k, v in sorted(uri.items(), key=lambda x: x[0].lower())}
        with open(json_path, 'w') as file:
            json.dump(uri, file, indent=2)

        print('\33[92m', 'Done', '\33[0m')

    def save_json(self, playlists, filename='metadata'):
        print(f'Saving {filename}.json locally...', end='')
        json_path = join(self.DATA_PATH, filename + '.json')
        with open(json_path, 'w') as file:
            json.dump(playlists, file, indent=2)

        print('\33[92m', 'Done', '\33[0m')
