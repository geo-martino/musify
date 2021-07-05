import glob
import json
import os
import re
import sys

from tqdm.auto import tqdm
from os.path import basename, dirname, exists, join, splitext
from urllib.request import urlopen
from urllib.error import URLError

import mutagen


class Data:

    def __init__(self):
        self.DATA_PATH = join(dirname(dirname(__file__)), 'data')
        if not exists(self.DATA_PATH):
            os.makedirs(self.DATA_PATH)

    def load_spotify_token(self):
        json_path = join(self.DATA_PATH, 'token.json')
        if not exists(json_path):
            return None

        print('Access token found. Loading stored access token.')
        with open(json_path, 'r') as file:
            token = json.load(file)
        return token

    def save_spotify_token(self, token):
        json_path = join(self.DATA_PATH, 'token.json')
        with open(json_path, 'w') as file:
            json.dump(token, file, indent=2)

    def get_m3u_metadata(self, playlists_path, verbose=True):
        filepaths = glob.glob(join(playlists_path, '*.m3u'))
        playlists = {}

        if verbose:
            print('Loading m3u playlists...', end=' ', flush=True)

        for playlist_path in filepaths:
            playlist_name = splitext(basename(playlist_path))[0]

            with open(playlist_path, 'r', encoding='utf-8') as m3u:
                playlist_metadata = [self.get_song_metadata(i, songpath.rstrip()) for i, songpath in enumerate(m3u) if
                                     exists(songpath.rstrip())]
                playlists[playlist_name] = playlist_metadata

        if verbose:
            print('\33[92m', 'Done', '\33[0m', sep='')

            print('Found the following playlists:')
            max_width = len(max(playlists.keys(), key=len))
            for name, playlist in sorted(playlists.items(), key=lambda x: x[0].lower()):
                length = str(len(playlist)) + ' tracks'
                print(f'{name : <{max_width}}', ':', '\33[92m', f'{length : >9} ', '\33[0m', sep='')

        return playlists

    @staticmethod
    def get_song_metadata(position, path):
        try:
            file_data = mutagen.File(path)
        except mutagen.MutagenError:
            print('\nERROR: Could not load', path, end=' ', flush=True)
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
                     'year': ['WM/Year']},
            'IMAGE': ['APIC', 'covr', 'WM/Picture']
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

        if file_extension == '.flac':
            has_image = bool(file_data.pictures)
        else:
            has_image = any([True for tag in file_data if any(im in tag for im in filetype_tags['IMAGE'])])
        metadata['has_image'] = has_image

        metadata['path'] = path
        return metadata

    def import_uri(self, playlists, filename='URIs'):
        json_path = join(self.DATA_PATH, filename + '.json')
        if not exists(json_path):
            return playlists

        print(f'Importing locally stored URIs...', end=' ', flush=True)

        with open(json_path, 'r') as file:
            uri = json.load(file)

        for playlist in playlists.values():
            for song in playlist:
                album = uri.get(song.get('album', None), {})
                if song['title'] in album:
                    song['uri'] = album[song['title']]

        print('\33[92m', 'Done', '\33[0m', sep='')
        return playlists

    def export_uri(self, playlists, filename='URIs'):
        json_path = join(self.DATA_PATH, filename + '.json')
        if exists(json_path):
            with open(json_path, 'r') as file:
                uri = json.load(file)
        else:
            uri = {}

        print(f'Saving URIs locally...', end=' ', flush=True)

        for playlist in playlists.values():
            for song in playlist:
                if 'uri' in song:
                    uri[song['album']] = uri.get(song['album'], {})
                    uri[song['album']][song['title']] = song['uri']

        uri = {k: v for k, v in sorted(uri.items(), key=lambda x: x[0].lower())}
        with open(json_path, 'w') as file:
            json.dump(uri, file, indent=2)

        print('\33[92m', 'Done', '\33[0m', sep='')

    def save_json(self, playlists, filename='data'):
        print(f'Saving {filename}.json...', end=' ', flush=True)
        json_path = join(self.DATA_PATH, filename + '.json')
        with open(json_path, 'w') as file:
            json.dump(playlists, file, indent=2)

        print('\33[92m', 'Done', '\33[0m', sep='')

    @staticmethod
    def uri_as_key(playlists):
        songs = {}
        for playlist in playlists.values():
            if 'tracks' in playlist:
                playlist = playlist['tracks']
            
            for song in playlist:
                songs[song['uri']] = {k: v for k, v in song.items() if k != 'uri'}
        
        return songs

    @staticmethod
    def embed_images(m3u, spotify):
        if len(m3u) == 0:
            return

        print('Embedding images to local files...')
        bar = tqdm(m3u.items(), desc='Embedding images: ', unit='songs', leave=False, file=sys.stdout)  # progress bar

        for i, (uri, song) in enumerate(bar):
            if song['has_image']:
                continue

            try:
                file = mutagen.File(song['path'])
                file_extension = splitext(song['path'])[1].lower()
            except mutagen.MutagenError:
                print('\nERROR: Could not load', song['path'], end=' ', flush=True)

            try:
                albumart = urlopen(spotify[uri]['image'])
            except URLError:
                continue

            for tag in dict(file.tags).copy():
                if any([t in tag for t in ['APIC', 'covr']]):
                    del file[tag]

            if file_extension == '.mp3':    
                file['APIC'] = mutagen.id3.APIC(
                    mime='image/jpeg',
                    type=mutagen.id3.PictureType.COVER_FRONT,
                    data=albumart.read()
                )
            elif file_extension == '.flac':   
                image = mutagen.flac.Picture()
                image.type = mutagen.id3.PictureType.COVER_FRONT
                image.mime = u"image/jpeg"
                image.data = albumart.read()

                file.clear_pictures()
                file.add_picture(image)
            elif file_extension == '.m4a':
                file["covr"] = [
                    mutagen.mp4.MP4Cover(albumart.read(), 
                                        imageformat=mutagen.mp4.MP4Cover.FORMAT_JPEG)
                ]
            elif file_extension == '.wma':
                pass

            albumart.close()
            file.save()
        
        print('\33[92m', f'Done. Modified {i+1} files.', '\33[0m', sep='')

    def no_images(self, m3u):
        no_images = {}
        for uri, song in m3u.items():
            if not song['has_image']:
                no_images[uri] = song
        
        return no_images