import os
import re
import sys
from os.path import basename, dirname, join, splitext

import mutagen
from titlecase import titlecase


class Misc:
    #############################################################
    ### Misc. functions
    #############################################################

    # THESE FUNCTIONS ARE AUTHOR SPECIFIC AND HAVE NOT BEEN BUILT FOR GENERAL USE.
    # All ARE UNTESTED AND EDGE CASES HAVE NOT BEEN CONSIDERED. USE WITH CAUTION.

    @staticmethod
    def caps(word: str, **kwargs) -> str:
        """
        Capitalisation cases for titlecase function.
        
        :param word: str. Word to consider.
        :return: str. Formatted word.
        """
        if word.upper() == word:
            # keep acronyms
            return word.upper()
        if 'feat.' in word.lower():
            # lower case feat. strings
            return word.lower()
        if word.lower() in ['is', 'das', 'de', 'im', 'ii', 'iii', 'y']:
            # keep lower cases for these words
            return word.lower()
        if word.lower() in ['thnks', 'mmrs', 'fkn', 'wndrwll', 'pts', 'o-o-h']:
            # keep title case for these words
            return word.title()
        if word in ['$ign']:
            # ignore these words
            return word

    def titlecase_folders(self, folders: dict, **kwargs) -> None:
        """
        Rename folders in title case from given tracks metadata. 
        Prompts user to confirm each folder name change.
        
        :param folders: dict. <folder name>: <list of dicts of track's metadata>
        """
        for folder, tracks in folders.items():
            # get album title from first track in the folder
            track = tracks[0]
            album = titlecase(track['album'].replace('"', "'"), callback=self.caps).strip()

            # sanitise folder name from illegal characters and title case string
            folder_old = folder
            folder = track['album'].replace(' / ', ' - ').replace('/', ' - ').replace(': ', ' - ').replace(':', '-')
            folder = titlecase(folder.replace('"', "'"), callback=self.caps).strip()
            folder = re.sub(r'[\\/*?:"<>|]', '', folder)

            # if album name has been changed, update folder name
            if track['album'] != album:
                old_path = dirname(track['path'])
                new_path = join(dirname(old_path), folder)

                # print old and new album names and folder names and ask user to confirm
                print(track['album'], album)
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

    def titlecase_files(self, folders: dict, prefix_start: str=None, **kwargs) -> None:
        """
        Rename track filename from its tags in title case from given tracks metadata.
        Replaces filename in format given with two options:
        - <track number> - <title> (if track number detected in filename with leading zeros)
        - <title>
        
        :param folders: dict. <folder name>: <list of dicts of track's metadata>
        :param start: str, default=None. Start tag renaming from this folder.
        """
        i = 0
        run = False

        for folder, tracks in folders.items():
            # check if folder name matches start folder if given
            if run or not prefix_start or (prefix_start and prefix_start in folder):
                run = True
            else:
                continue

            # extract path to folder from first track
            path = dirname(tracks[0]['path'])

            print(f'\n----- {folder} -----')
            for track in tracks:
                # get filename and extension
                filename = basename(splitext(track['path'])[0])
                file_ext = splitext(track['path'])[1]

                # sanitise and title case title tag
                title = track['title'].replace(' / ', ' - ').replace('/', ' - ')
                title = title.replace(': ', ' - ').replace(':', ' - ').replace('"', "'")
                title = titlecase(title, callback=self.caps).strip()
                title = re.sub(r'[\\/*?:"<>|]', '', title)

                # check filename changes are necessary
                if title not in filename.strip() and title != filename.capitalize():
                    i += 1
                    if track['track'] is not None:  # if track number in file tags
                        # add leading 0 to track number string
                        track = f"0{track['track']}" if track['track'] // 10 == 0 else str(track['track'])

                        if track.strip() in filename[:3].strip():  # add track number to filename if already in filename
                            text = f'{track} - {title}'
                        else:  # just use title as filename
                            text = title
                    else:  # just use title as filename
                        text = title

                    # show new filename and define new and old paths
                    print(text)
                    old_path = track['path']
                    new_path = join(path, text + file_ext)

                    try:  # rename file
                        os.rename(old_path, new_path)
                    except FileNotFoundError:  # skip if file not found
                        continue

        print('\33[92m', f'Done. Modified {i + 1} URIs', '\33[0m')

    def tags_from_filename(self, folders: dict, no_rename: list=None, prefix_start: str=None, **kwargs) -> None:
        """
        Replace tags from filename. Accepts filenames in forms:
        - <year> - <title>
        - <track number> - <title> (track number may include leading zeros)
        - <title>
        
        Automatically replaces filenames with only case-sensitive modifications, or track number changes.
        Otherwise, prompts user to confirm changes before modification.
        
        :param folders: dict. In format, <folder name>: <list of dicts of track's metadata>
        :param no_rename: list, default=None. Folders to skip.
        :param start: str, default=None. Start tag renaming from this folder.
        """
        run = False

        for folder, tracks in folders.items():
            # check if folder name matches start folder if given
            if run or not prefix_start or (prefix_start and folder.lower().startswith(prefix_start)):
                run = True
            else:
                continue

            for track in tracks:
                # system specific regex tag extraction from filepath
                if sys.platform == 'win32':
                    regex_str = r'(?:(?:^.*\\(?P<year>\b\d{4}?\b)|^.*\\(?P<track>\b\d{1,3}\b)?)(?:\W+|.*\\)?(?P<title>.*)(?P<ext>\..*)$)'
                else:
                    regex_str = r'(?:(?:^.*/(?P<year>\b\d{4}?\b)|^.*/(?P<track>\b\d{1,3}\b)?)(?:\W+|.*/)?(?P<title>.*)(?P<ext>\..*)$)'

                # extract tags to group dict
                d = re.search(regex_str, track['path']).groupdict()

                if track['album'] not in no_rename:  # if album not in no_rename list
                    # title case and replace double quotes with single
                    d['album'] = titlecase(track['album'].replace('"', "'"), callback=self.caps).strip()

                # open file, extract file extension, and define tag names for this file type
                file_data, file_ext = self.load_file(track['path'], **kwargs)
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
                                        file_data[tag_var] = [(int(tag), len(tracks))]
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
