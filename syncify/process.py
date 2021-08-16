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


class Process:

    def extract_images(self, metadata, kind='local', foldername='local', dim=True, verbose=True):
        """
        Extract and save all embedded images from local files or Spotify tracks.
        
        :param metadata: dict. Dict of metadata for local or Spotify data. 
            Local: <name>: <list of songs metadata>. Spotify: <name>: <<'tracks'>: <list of songs metadata>>
        :param kind: str, default='local'. Type of metadata passed to function, 'local' or 'spotify'
        :param foldername: str, default='local'. Name of folder to store images i.e. $DATA_PATH/images/<foldername>
        :param dim: bool, default=True. Add dimensions to image filenames on export as suffix in parentheses.
        :param verbose: bool, default=True. Persist progress bars if True.
        """
        # define overall path and progress bar
        images_path = join(self.DATA_PATH, 'images', foldername)
        bar = tqdm(metadata.items(), desc='Extracting images: ', unit='folders', leave=verbose, file=sys.stdout)

        if kind == 'local':  # if extracting images from local data
            for name, songs in bar:
                for song in songs:
                    # load file as mutagen object
                    file_data, file_ext = self.load_file(song)
                    if not file_data or not file_ext:
                        continue

                    # define save path for this song image
                    save_path = splitext(song['path'].replace(self.MUSIC_PATH, '').lstrip(sep))[0]
                    save_path = join(images_path, save_path)

                    # tags for images for .mp3, .m4a, and .wma files
                    tags = ['APIC', 'covr', 'WM/Picture']
                    img = None

                    # extension specific processing                  
                    if file_ext == '.flac':
                        if len(file_data.pictures) > 0:
                            img = file_data.pictures[0].data
                    else:
                        for tag in tags:
                            for file_tag in file_data:
                                if tag in file_tag and not img:
                                    if '.mp3' in file_ext:
                                        img = file_data[file_tag].data
                                    elif '.m4a' in file_ext:
                                        img = bytes(file_data[file_tag][0])
                                    elif '.wma' in file_ext:
                                        img = file_data[file_tag][0].value
                                    break

                    # if no image found, skip
                    if not img:
                        continue

                    # create save folder for this song if doesn't exist
                    if not exists(split(save_path)[0]):
                        os.makedirs(split(save_path)[0])

                    # load image
                    img = Image.open(BytesIO(img))

                    # determine embedded image file type
                    if 'png' in img.format.lower():
                        img_ext = '.png'
                    else:
                        img_ext = '.jpg'

                    if dim:  # add dimensions to filename and save
                        dim = f" ({'x'.join(str(n) for n in img.size)})"
                        img.save(save_path + dim + img_ext)
                    else:  # save with standard filename
                        img.save(save_path + img_ext)

        else:  # extracting images from Spotify data
            for name, songs in bar:
                # if metadata given in Spotify based <url> + <tracks> format
                if isinstance(songs, dict) and 'tracks' in songs:
                    songs = songs['tracks']

                # sanitise playlist name for folder
                name = re.sub(r'[\\/*?:"<>|]', '', name)
                for song in songs:
                    try:  # open image from link
                        img = Image.open(BytesIO(urlopen(song['image']).read()))
                    except URLError:
                        continue

                    # create filename and save path form playlist name, position, and title
                    title = re.sub(r'[\\/*?:"<>|]', '', song['title'])
                    song = f"{song['position']} - {title}"
                    save_path = join(images_path, name, song)

                    # create save folder for this song if doesn't exist
                    if not exists(split(save_path)[0]):
                        os.makedirs(split(save_path)[0])

                    if dim:  # add dimensions to filename and save
                        dim = f" ({'x'.join(str(n) for n in img.size)})"
                        img.save(save_path + dim + '.jpg')
                    else:  # save with standard filename
                        img.save(save_path + '.jpg')

    def embed_images(self, local, spotify, replace=False):
        """
        Embed images to local files from linked Spotify URI images.
        
        :param local: dict. <song URI>: <local song metadata>.
        :param spotify: dict. <song URI>: <spotify song metadata>
        :param replace: bool, default=False. Replace locally embedded images if True. 
            Otherwise, only add images to files with no embedded image.
        """
        if len(local) == 0:  # return if no local files given
            return

        # progress bar
        bar = tqdm(local.items(), desc='Embedding images: ', unit='songs', leave=False, file=sys.stdout)
        i = 1

        for i, (uri, song) in enumerate(bar, 1):
            # skip if not replacing embedded images
            if not replace and song['has_image']:
                continue

            # load file as mutagen object
            file_data, file_ext = self.load_file(song)
            if not file_data or not file_ext:
                continue

            try:  # open image from link
                albumart = urlopen(spotify[uri]['image'])
            except URLError:
                continue

            # delete embedded images for .mp3 and .m4a files
            for tag in dict(file_data.tags).copy():
                if any([t in tag for t in ['APIC', 'covr']]):
                    del file_data[tag]

            # file extension specific embedding
            if file_ext == '.mp3':
                file_data['APIC'] = mutagen.id3.APIC(
                    mime='image/jpeg',
                    type=mutagen.id3.PictureType.COVER_FRONT,
                    data=albumart.read()
                )
            elif file_ext == '.flac':
                image = mutagen.flac.Picture()
                image.type = mutagen.id3.PictureType.COVER_FRONT
                image.mime = u"image/jpeg"
                image.data = albumart.read()

                # replace embedded image
                file_data.clear_pictures()
                file_data.add_picture(image)
            elif file_ext == '.m4a':
                file_data["covr"] = [
                    mutagen.mp4.MP4Cover(albumart.read(), imageformat=mutagen.mp4.MP4Cover.FORMAT_JPEG)
                ]
            elif file_ext == '.wma':
                # not yet coded
                pass

            # close link and save updated file tags
            albumart.close()
            file_data.save()

        print('\33[92m', f'Modified {i} files', '\33[0m', sep='')

    # THE FOLLOWING FUNCTIONS ARE AUTHOR SPECIFIC AND HAVE NOT BEEN BUILT FOR GENERAL USE.
    # USE WITH CAUTION.

    @staticmethod
    def caps(word):
        """
        Capitalisation cases for titlecase function.
        
        :param word: str. Word to consider.
        :return: str. Formatted word.
        """
        if word.upper() == word:  # keep acronyms
            return word.upper()
        if 'feat.' in word.lower():  # lower case feat. strings
            return word.lower()
        if word.lower() in ['is', 'das', 'de', 'im', 'ii', 'iii', 'y']:  # keep lower cases for these words
            return word.lower()
        if word.lower() in ['thnks', 'mmrs', 'fkn', 'wndrwll', 'pts', 'o-o-h']:  # keep title case for these words
            return word.title()
        if word in ['$ign']:  # ignore these words
            return word

    def titlecase_folders(self, folders):
        """
        Rename folders in title case from given songs metadata. Prompts user to confirm each folder name change.
        
        :param folders: dict. In format, <folder name>: <list of dicts of song metadata>
        """
        for folder, songs in folders.items():
            # get album title from first track in the folder
            song = songs[0]
            album = titlecase(song['album'].replace('"', "'"), callback=self.caps).strip()

            # sanitise folder name from illegal characters and title case string
            folder_old = folder
            folder = song['album'].replace(' / ', ' - ').replace('/', ' - ').replace(': ', ' - ').replace(':', '-')
            folder = titlecase(folder.replace('"', "'"), callback=self.caps).strip()
            folder = re.sub(r'[\\/*?:"<>|]', '', folder)

            # if album name has been changed, update folder name
            if song['album'] != album:
                old_path = dirname(song['path'])
                new_path = join(dirname(old_path), folder)

                # print old and new album names and folder names and ask user to confirm
                print(song['album'], album)
                print(folder_old)
                yes = input(folder) == 'y'
                print()

                if yes:  # rename folder
                    try:
                        os.rename(old_path, new_path)
                    except FileNotFoundError:  # skip if file not found
                        print('error')
                        print()
                        continue

    def titlecase_files(self, folders, start=None):
        """
        Rename song filename from its tags in title case from given songs metadata.
        Replaces filename in format given with two options:
        - <track number> - <title> (if track number detected in filename with leading zeros)
        - <title>
        
        :param folders: dict. In format, <folder name>: <list of dicts of song metadata>
        :param start: str, default=None. Start tag renaming from this folder.
        """
        i = 0
        run = False

        for folder, songs in folders.items():
            # check if folder name matches start folder if given
            if run or not start or (start and start in folder):
                run = True
            else:
                continue

            # extract path to folder from first track
            path = dirname(songs[0]['path'])

            print(f'\n----- {folder} -----')
            for song in songs:
                # get filename and extension
                filename = basename(splitext(song['path'])[0])
                file_ext = splitext(song['path'])[1]

                # sanitise and title case title tag
                title = song['title'].replace(' / ', ' - ').replace('/', ' - ').replace(': ', ' - ').replace(':',
                                                                                                             ' - ').replace(
                    '"', "'")
                title = titlecase(title, callback=self.caps).strip()
                title = re.sub(r'[\\/*?:"<>|]', '', title)

                # check filename changes are necessary
                if title not in filename.strip() and title != filename.capitalize():
                    i += 1
                    if song['track'] is not None:  # if track number in file tags
                        # add leading 0 to track number string
                        track = f"0{song['track']}" if song['track'] // 10 == 0 else str(song['track'])

                        if track.strip() in filename[:3].strip():  # add track number to filename if already in filename
                            text = f'{track} - {title}'
                        else:  # just use title as filename
                            text = title
                    else:  # just use title as filename
                        text = title

                    # show new filename and define new and old paths
                    print(text)
                    old_path = song['path']
                    new_path = join(path, text + file_ext)

                    try:  # rename file
                        os.rename(old_path, new_path)
                    except FileNotFoundError:  # skip if file not found
                        continue

        print('\33[92m', f'Done. Modified {i + 1} URIs', '\33[0m')

    def tags_from_filename(self, folders, no_rename=None, start=None):
        """
        Replace tags from filename. Accepts filenames in forms:
        - <year> - <title>
        - <track number> - <title> (track number may include leading zeros)
        - <title>
        
        Automatically replaces filenames with only case-sensitive modifications, or track number changes.
        Otherwise, prompts user to confirm changes before modification.
        
        :param folders: dict. In format, <folder name>: <list of dicts of song metadata>
        :param no_rename: list, default=None. Folders to skip.
        :param start: str, default=None. Start tag renaming from this folder.
        """
        if no_rename:  # Author specific folders to ignore
            no_rename = ["Disney's The Lion King", "Downloads - Cheese-tastic 1", "Downloads - Cheese-tastic 2",
                         "Downloads - Cheese-tastic 3", "Downloads - Cheese-tastic 4", "Downloads - Cheese-tastic 5",
                         "Downloads - Cheese-tastic 6", "Downloads - Cheese-tastic 7",
                         "Dvorak - Symphony No. 9 in E minor, 'From the New World' Op. 95, B. 178", "One By One",
                         "Safe The Second", "Safe The Second (Extras)", "There Is Nothing Left to Lose"]
        run = False

        for folder, songs in folders.items():
            # check if folder name matches start folder if given
            if run or not start or (start and folder.lower().startswith(start)):
                run = True
            else:
                continue

            for song in songs:
                # system specific regex tag extraction from filepath
                if sys.platform == 'win32':
                    regex_str = r'(?:(?:^.*\\(?P<year>\b\d{4}?\b)|^.*\\(?P<track>\b\d{1,3}\b)?)(?:\W+|.*\\)?(?P<title>.*)(?P<ext>\..*)$)'
                else:
                    regex_str = r'(?:(?:^.*/(?P<year>\b\d{4}?\b)|^.*/(?P<track>\b\d{1,3}\b)?)(?:\W+|.*/)?(?P<title>.*)(?P<ext>\..*)$)'

                # extract tags to group dict
                d = re.search(regex_str, song['path']).groupdict()

                if song['album'] not in no_rename:  # if album not in no_rename list
                    # title case and replace double quotes with single
                    d['album'] = titlecase(song['album'].replace('"', "'"), callback=self.caps).strip()

                # open file, extract file extension, and define tag names for this file type
                file_data, file_ext = self.load_file(path)
                if not file_data or not file_ext:
                    continue
                ext = d['ext'].lower()
                tags = self.filetype_tags[d.pop('ext').lower()]
                changed = {}

                for name, tag in d.items():
                    if tag:  # if tag found in filename
                        tag = tag.strip()  # strip whitespace
                        for tag_var in tags[name]:  # loop through possible tag type names for this file type
                            # print(tag_var, file_data[tag_var], tag)

                            # if tag type name in this file's tags
                            if tag_var in file_data and re.sub(r'[\\/:*?"<>|\-_]+', '', tag) not in re.sub(
                                    r'[\\/:*?"<>|\-_]+', '', str(file_data[tag_var])):
                                # store changed tags for this file
                                changed[name] = file_data[tag_var]

                                # file type specific tag modification
                                if ext == '.flac':
                                    file_data[tag_var] = tag
                                elif ext == '.mp3':
                                    file_data[tag_var] = getattr(mutagen.id3, tag_var)(3, tag)
                                elif ext == '.m4a':
                                    if name == 'track':
                                        file_data[tag_var] = [(int(tag), len(songs))]
                                    else:
                                        file_data[tag_var] = [tag]
                                elif ext == '.wma':
                                    file_data[tag_var] = mutagen.asf.ASFUnicodeAttribute(tag)

                                break
                if changed:  # if a tag has been modified
                    # print old and new tags
                    [print(f'{k}: {v}') for k, v in changed.items()]
                    [print(f'{k}: {d[k]}') for k in changed]

                    track_match = False
                    if 'track' in changed:  # if track number has been changed
                        # if the only change is adding a leading zero, track_match = True
                        if str(d['track'])[0] == '0':
                            track_match = True
                    else:  # True if track number has not been changed
                        track_match = True

                    if 'title' in changed:  # if title has been changed
                        # if only case changes have occurred, title_match = True
                        title_match = d['title'].lower().strip() in str(changed['title']).lower().strip()
                    else:  # True if title has not been changed
                        title_match = True

                    if 'album' in changed:  # if album has been changed
                        # if only case changes have occurred, album_match = True
                        album_match = d['album'].lower().strip() in str(changed['album']).lower().strip()
                    else:  # True if album has not been changed
                        album_match = True

                    if all([title_match, album_match, track_match]):
                        # do not prompt user for confirmation if all above conditions are True
                        skip = False
                    else:  # prompt user for confirmation
                        skip = input(">>>>>> 'n' to discard changes") == 'n'

                    if not skip:  # save tags
                        print('\33[92;1m SAVED \33[0m')
                        file_data.save()
                    print()
