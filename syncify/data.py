import glob
import json
import os
import re
import sys
from io import BytesIO
from os.path import basename, dirname, exists, join, sep, split, splitext
from urllib.error import URLError
from urllib.request import urlopen

import mutagen
from PIL import Image
from titlecase import titlecase
from tqdm.auto import tqdm


class Data:

    def __init__(self):
        self.all_files = glob.glob(join(self.MUSIC_PATH, '*', '**', '*'), recursive=True)
        self.filetype_tags = {
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

    def get_m3u_metadata(self, in_playlists=None, verbose=True):
        self.all_files = glob.glob(join(self.MUSIC_PATH, '*', '**', '*'), recursive=True)
        filepaths = glob.glob(join(self.PLAYLISTS_PATH, '*.m3u'))
        playlists = {}

        playlist_bar = tqdm(filepaths,
                            desc='Loading m3u playlists: ',
                            unit='playlists',
                            leave=verbose,
                            file=sys.stdout)

        for playlist_path in playlist_bar:
            playlist_name = splitext(basename(playlist_path))[0]
            if in_playlists and playlist_name not in in_playlists:
                continue

            with open(playlist_path, 'r', encoding='utf-8') as m3u:
                files = [line.rstrip() for line in m3u]

            if any([path in files[0] for path in self.OTHER_PATHS]):
                sub = self.OTHER_PATHS[0] if files[0].startswith(self.OTHER_PATHS[0]) else self.OTHER_PATHS[1]
                files = [file.replace(sub, self.MUSIC_PATH) for file in files]

                if '/' in self.MUSIC_PATH:
                    files = [file.replace('\\', '/') for file in files]
                else:
                    files = [file.replace('/', '\\') for file in files]

            if len(files) > 100:
                files = tqdm(files, desc=f'{playlist_name}: ', unit='songs', leave=False, file=sys.stdout)
            playlist_metadata = [self.get_song_metadata(file, i, verbose, playlist_name)
                                 for i, file in enumerate(files)]
            playlists[playlist_name] = [song for song in playlist_metadata if song]

        if verbose:
            print('Found the following playlists:')
            max_width = len(max(playlists.keys(), key=len)) + 1

            for name, playlist in sorted(playlists.items(), key=lambda x: x[0].lower()):
                length = str(len(playlist)) + ' tracks'
                print(f'{name : <{max_width}}', ': ', '\33[92m', f'{length : >11} ', '\33[0m', sep='')

        return playlists

    def get_all_metadata(self, ex_playlists=None, ex_folders=None, in_folders=None, verbose=True):
        exclude = set()
        if ex_playlists:
            if ex_playlists is True:
                ex_playlists = self.PLAYLISTS_PATH
            playlists = glob.glob(join(ex_playlists, '*.m3u'))

            for playlist in playlists:
                with open(playlist, 'r', encoding='utf-8') as m3u:
                    files = [file.rstrip() for file in m3u]

                if any([path in files[0] for path in self.OTHER_PATHS]):
                    sub = self.OTHER_PATHS[0] if files[0].startswith(self.OTHER_PATHS[0]) else self.OTHER_PATHS[1]
                    files = [file.replace(sub, self.MUSIC_PATH) for file in files]

                    if '/' in self.MUSIC_PATH:
                        files = [file.replace('\\', '/') for file in files]
                    else:
                        files = [file.replace('/', '\\') for file in files]

                exclude = exclude | set(files)

        if not ex_folders:
            ex_folders = []

        files = [file for file in glob.glob(join(self.MUSIC_PATH, '*', '**', '*'), recursive=True)
                 if any([file.lower().endswith(ext) for ext in ['.flac', '.mp3', '.m4a', '.wma']])
                 and file not in exclude and basename(dirname(file)) not in ex_folders]

        if in_folders:
            files = [file for file in files if basename(dirname(file)) in in_folders]

        folder_metadata = {}
        bar = tqdm(files, desc='Loading library: ', unit='songs', leave=verbose, file=sys.stdout)

        for file in bar:
            folder = basename(dirname(file))
            song = self.get_song_metadata(file, verbose=verbose)

            if song:
                folder_metadata[folder] = folder_metadata.get(folder, [])
                folder_metadata[folder].append(song)

        return folder_metadata

    def get_song_metadata(self, path, position=None, verbose=True, playlist=None):
        file_ext = splitext(path)[1].lower()
        if file_ext not in self.filetype_tags:
            return

        try:
            file_data = mutagen.File(path)
        except mutagen.MutagenError:
            for file_path in self.all_files:
                if file_path.lower() == path.lower():
                    path = file_path
                    break

            try:
                file_data = mutagen.File(path)
            except mutagen.MutagenError:
                if verbose:
                    print('ERROR: Could not load', path, f'({playlist})', flush=True)
                return

        metadata = {'position': position}

        for key, tags in self.filetype_tags.get(file_ext, {'': []}).items():
            for tag in tags:
                if file_ext == '.wma':
                    metadata[key] = file_data.get(tag, [mutagen.asf.ASFUnicodeAttribute(None)])[0].value
                elif file_ext == '.m4a' and key == 'track':
                    metadata[key] = file_data.get(tag, [None])[0][0]
                else:
                    metadata[key] = file_data.get(tag, [None])[0]

                if len(str(metadata[key]).strip()) == 0:
                    metadata[key] = None

                if metadata[key]:
                    if isinstance(metadata[key], str):
                        metadata[key] = metadata[key].strip()
                    break

        if metadata.get('track') and not isinstance(metadata.get('track'), int):
            metadata['track'] = int(re.sub('[^0-9]', '', metadata['track']))

        try:
            metadata['year'] = int(re.sub('[^0-9]', '', metadata.get('year', ''))[:4])
        except (ValueError, TypeError):
            metadata['year'] = 0

        metadata['length'] = file_data.info.length

        if file_ext == '.flac':
            metadata['has_image'] = bool(file_data.pictures)
        else:
            metadata['has_image'] = any([True for tag in file_data
                                         if any(im in tag for im in filetype_tags['IMAGE'])])

        metadata['path'] = path

        return metadata

    def import_uri(self, playlists, filename='URIs'):
        json_path = join(self.DATA_PATH, filename + '.json')
        if not exists(json_path):
            return playlists

        print('Importing locally stored URIs...', end='', flush=True)

        with open(json_path, 'r') as file:
            uri = json.load(file)

        i = 0

        for playlist in playlists.values():
            for song in playlist:
                filename = splitext(basename(song['path']))[0]
                album = {k.lower().strip(): v for k, v in uri.get(song.get('album'), {}).items()}

                if filename.lower().strip() in album:
                    i += 1
                    song['uri'] = album.get(filename.lower().strip())

        print('\33[92m', f'Done. Imported {i} URIs', '\33[0m')
        return playlists

    def export_uri(self, playlists, filename='URIs'):
        json_path = join(self.DATA_PATH, filename + '.json')
        if exists(json_path):
            with open(json_path, 'r') as file:
                uri = json.load(file)
        else:
            uri = {}

        print('Saving URIs locally...', end='', flush=True)
        i = 0

        for playlist in playlists.values():
            for song in playlist:
                if 'uri' in song:
                    i += 1
                    filename = splitext(basename(song['path']))[0].lower()
                    uri[song['album']] = uri.get(song['album'], {})
                    uri[song['album']][filename] = song['uri']

        uri = {k: {k: v for k, v in sorted(v.items(), key=lambda x: x[0].lower())}
               for k, v in sorted(uri.items(), key=lambda x: x[0].lower())}
        with open(json_path, 'w') as file:
            json.dump(uri, file, indent=2)

        print('\33[92m', f'Done. Saved {i} URIs', '\33[0m')

    def save_json(self, playlists, filename='data'):
        print(f'Saving {filename}.json...', end=' ', flush=True)
        json_path = join(self.DATA_PATH, filename + '.json')

        with open(json_path, 'w') as file:
            json.dump(playlists, file, indent=2)

        print('\33[92m', 'Done', '\33[0m', sep='')

    def load_json(self, filename):
        json_path = join(self.DATA_PATH, filename + '.json')
        with open(json_path, 'r') as file:
            return json.load(file)

    @staticmethod
    def uri_as_key(playlists):
        songs = {}
        for playlist in playlists.values():
            if isinstance(playlist, dict):
                playlist = playlist['tracks']

            for song in playlist:
                if 'uri' in song:
                    songs[song['uri']] = {k: v for k, v in song.items() if k != 'uri'}

        return songs

    @staticmethod
    def embed_images(local, spotify, replace=False):
        if len(local) == 0:
            return

        bar = tqdm(local.items(), desc='Embedding images: ', unit='songs', leave=False, file=sys.stdout)
        i = 0

        for i, (uri, song) in enumerate(bar):
            if not replace and song['has_image']:
                continue

            try:
                file = mutagen.File(song['path'])
                file_extension = splitext(song['path'])[1].lower()
            except mutagen.MutagenError:
                print('\nERROR: Could not load', song['path'], end=' ', flush=True)
                continue

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
                    mutagen.mp4.MP4Cover(albumart.read(), imageformat=mutagen.mp4.MP4Cover.FORMAT_JPEG)
                ]
            elif file_extension == '.wma':
                pass

            albumart.close()
            file.save()

        print('\33[92m', f'Modified {i} files', '\33[0m', sep='')

    @staticmethod
    def no_images(local):
        no_images = {}
        for uri, song in local.items():
            if not song['has_image']:
                no_images[uri] = song

        return no_images

    def extract_images(self, metadata, kind='local', foldername='local', dim=True, verbose=True):
        images_path = join(self.DATA_PATH, 'images', foldername)
        bar = tqdm(metadata.items(), desc='Extracting images: ', unit='folders', leave=verbose, file=sys.stdout)

        if kind == 'local':
            for name, songs in bar:
                for song in songs:
                    try:
                        file = mutagen.File(song['path'])
                        file_ext = splitext(song['path'])[1].lower()
                    except mutagen.MutagenError:
                        print('\nERROR: Could not load', song['path'], end=' ', flush=True)
                        continue

                    save_path = splitext(song['path'].replace(self.MUSIC_PATH, '').lstrip(sep))[0]
                    save_path = join(images_path, save_path)

                    tags = ['APIC', 'covr', 'WM/Picture']

                    img = None
                    if file_ext == '.flac':
                        if len(file.pictures) > 0:
                            img = file.pictures[0].data
                    else:
                        for tag in tags:
                            for file_tag in file:
                                if tag in file_tag and not img:
                                    if '.mp3' in file_ext:
                                        img = file[file_tag].data
                                    elif '.m4a' in file_ext:
                                        img = bytes(file[file_tag][0])
                                    elif '.wma' in file_ext:
                                        img = file[file_tag][0].value
                                    break

                    if not img:
                        continue

                    if not exists(split(save_path)[0]):
                        os.makedirs(split(save_path)[0])

                    img = Image.open(BytesIO(img))

                    if 'png' in img.format.lower():
                        img_ext = '.png'
                    else:
                        img_ext = '.jpg'

                    if dim:
                        dim = f" ({'x'.join(str(n) for n in img.size)})"
                        img.save(save_path + dim + img_ext)
                    else:
                        img.save(save_path + img_ext)
        else:
            for name, songs in bar:
                name = re.sub(r'[\\/*?:"<>|]', '', name)
                for song in songs:
                    try:
                        albumart = urlopen(song['image']).read()
                    except URLError:
                        continue

                    title = re.sub(r'[\\/*?:"<>|]', '', song['title'])
                    song = f"{song['position']} - {title}"
                    save_path = join(images_path, name, song)
                    img = Image.open(BytesIO(albumart))

                    if not exists(split(save_path)[0]):
                        os.makedirs(split(save_path)[0])

                    if dim:
                        dim = f" ({'x'.join(str(n) for n in img.size)})"
                        img.save(save_path + dim + '.jpg')
                    else:
                        img.save(save_path + '.jpg')
                        
                        
    def caps(word, **kwargs):
        if word.upper() == word:
            return word.upper()
        if 'feat.' in word.lower():
            return word.lower()
        if word.lower() in ['is', 'das', 'de', 'im', 'ii', 'iii', 'y']:
            return word.lower()
        if word.lower() in ['thnks', 'mmrs', 'fkn', 'wndrwll', 'pts', 'o-o-h']:
            return word.title()
        if word in ['$ign']:
            return word
    
    def titlecase_folders(self, folders):
        for folder, songs in folders.items():
            song = songs[0]
            album = titlecase(song['album'].replace('"', "'"), callback=self.caps).strip()
            
            folder_old = folder
            folder = song['album'].replace(' / ', ' - ').replace('/', ' - ').replace(': ', ' - ').replace(':', '-')
            folder = titlecase(folder.replace('"', "'"), callback=self.caps).strip()
            folder = re.sub(r'[\\/*?:"<>|]', '', folder)
            if song['album'] != album:
                old_path = dirname(song['path'])
                new_path = join(dirname(old_path), folder)
                
                print(song['album'], album)
                print(folder_old)
                yes = input(folder) == 'y'
                print()
                
                if yes:
                    try:
                        os.rename(old_path, new_path)
                    except FileNotFoundError:
                        print('error')
                        print()
                        continue
    
    def titlecase_files(self, folders, start=None):
        i = 0
        run = False
        
        for folder, songs in folders.items():
            if run or (start and start in folder):
                run = True
            else:
                continue
                
            path = dirname(songs[0]['path'])
            
            print(f'\n----- {folder} -----')
            for song in songs:
                filename = basename(splitext(song['path'])[0])
                file_ext = splitext(song['path'])[1]
                
                title = song['title'].replace(' / ', ' - ').replace('/', ' - ').replace(': ', ' - ').replace(':', ' - ').replace('"', "'")
                title = titlecase(title, callback=caps).strip()
                title = re.sub(r'[\\/*?:"<>|]', '', title)
                
                if title not in filename.strip() and title != filename.capitalize():
                    i += 1
                    if song['track'] is not None:
                        track = f"0{song['track']}" if song['track'] // 10 == 0 else str(song['track'])
                        if track.strip() in filename[:3].strip():
                            text = f'{track} - {title}'
                        else:
                            text = title
                    else:
                        text = title
                        
                    print(text)
                    
                    old_path = song['path']
                    new_path = join(path, text + file_ext)
                    
                    try:
                        os.rename(old_path, new_path)
                    except FileNotFoundError:
                        continue
                
        print('\33[92m', f'Done. Modified {i + 1} URIs', '\33[0m')
        

    def tags_from_filename(self, folders, no_rename=None, start=None):
        if no_rename:
            no_rename = ["Disney's The Lion King", "Downloads - Cheese-tastic 1", "Downloads - Cheese-tastic 2", 
                         "Downloads - Cheese-tastic 3", "Downloads - Cheese-tastic 4", "Downloads - Cheese-tastic 5", 
                         "Downloads - Cheese-tastic 6", "Downloads - Cheese-tastic 7", 
                         "Dvorak - Symphony No. 9 in E minor, 'From the New World' Op. 95, B. 178", "One By One", 
                         "Safe The Second", "Safe The Second (Extras)", "There Is Nothing Left to Lose"]
        run = False

        for folder, songs in folders.items():
            if run or (start and folder.lower().startswith(start)):
                run = True
            else:
                continue
            
            for song in songs:
                if sys.platform == 'win32':
                    regex_str = r'(?:(?:^.*\\(?P<year>\b\d{4}?\b)|^.*\\(?P<track>\b\d{1,3}\b)?)(?:\W+|.*\\)?(?P<title>.*)(?P<ext>\..*)$)'
                else:
                    regex_str = r'(?:(?:^.*/(?P<year>\b\d{4}?\b)|^.*/(?P<track>\b\d{1,3}\b)?)(?:\W+|.*/)?(?P<title>.*)(?P<ext>\..*)$)'
                d = re.search(regex_str, song['path']).groupdict()
                
                if song['album'] not in no_rename:
                    d['album'] = titlecase(song['album'].replace('"', "'"), callback=self.caps).strip()

                file = mutagen.File(song['path'])

                ext = d['ext'].lower()
                tags = self.filetype_tags[d.pop('ext').lower()]
                changed = {}

                for name, tag in d.items():
                    if tag:
                        tag = tag.strip()
                        for tag_var in tags[name]:
                            # print(tag_var, file[tag_var], tag)
                            if tag_var in file and re.sub(r'[\\/:*?"<>|\-_]+', '', tag) not in re.sub(r'[\\/:*?"<>|\-_]+', '', str(file[tag_var])):
                                changed[name] = file[tag_var]
                                if ext == '.flac':
                                    file[tag_var] = tag
                                elif ext == '.mp3':
                                    file[tag_var] = getattr(mutagen.id3, tag_var)(3, tag)
                                elif ext == '.m4a':
                                    if name == 'track':
                                        file[tag_var] = [(int(tag), len(songs))]
                                    else:
                                        file[tag_var] = [tag]
                                elif ext == '.wma':
                                    file[tag_var] = mutagen.asf.ASFUnicodeAttribute(tag)

                                break
                if changed:
                    [print(f'{k}: {v}') for k, v in changed.items()]
                    [print(f'{k}: {d[k]}') for k in changed]
                    
                    title_match = False
                    track_match = False
                    album_match = False
                    
                    
                    if 'track' in changed:
                        if str(d['track'])[0] == '0':
                            track_match = True
                    else:
                        track_match = True
                        
                    if 'title' in changed:
                        title_match = d['title'].lower().strip() in str(changed['title']).lower().strip()
                    else:
                        title_match = True
                        
                    if 'album' in changed:
                        album_match = d['album'].lower().strip() in str(changed['album']).lower().strip()
                    else:
                        album_match = True
                    
                    if all([title_match, album_match, track_match]):
                        skip = False
                    else:
                        skip = input(">>>>>> 'n' to discard changes") == 'n'

                    if not skip:
                        print('\33[92;1m SAVED \33[0m')
                        file.save()
                    print()