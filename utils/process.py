import os
import re
import sys
from io import BytesIO
from datetime import datetime as dt
from os.path import basename, dirname, exists, join, split, splitext
from urllib.error import URLError
from urllib.request import urlopen

import json
from time import sleep

import mutagen
from PIL import Image
from tqdm.auto import tqdm


class Process():

    _sort_ignore_words = ["The", "A"]

    @staticmethod
    def _make_list(data) -> list:
        return data if isinstance(data, list) else [data]

    @staticmethod
    def _str_ts_to_int(timestamp_str: str) -> int:
        if timestamp_str:
            return dt.strptime(timestamp_str, "%d/%m/%Y %H:%M:%S").timestamp()
        return 0

    def _strip_ignore_words(self, value: str):
        new_value = value
        not_special = False
        if isinstance(value, str):
            not_special = not any(value.startswith(c) for c in list('!"£$%^&*()_+-=…'))
            for word in self._sort_ignore_words:
                new_value = re.sub(f'^{word} ', '', value)
                if new_value != value:
                    break
        elif new_value is None:
            new_value = 0
        return not_special, new_value

    #############################################################
    ## Update tags
    #############################################################
    def update_file_tags(self, playlists: dict, tags: list = None,
                         replace: bool = False, dry_run: bool = True, **kwargs) -> None:
        """
        Update file's tags from given dictionary of tags.

        :param playlists: dict. Metadata in form <name>: <list of dicts of track's metadata>
        :param tags: list. Tag keys to be updated.
        :param replace: bool, default=False. Destructively replace tags in each file.
        :param dry_run: bool, default=True. Run function, but do not modify file at all.
        """
        tracks_all = [t for tracks in playlists.values() for t in tracks]
        print()
        self._logger.info(
            f"\33[1;95m -> \33[1;97mUpdating tags in {len(tracks_all)} files: {tags} \33[0m")
        if tags is None:
            self._logger.info(f"\33[93mSkipping: No tags given to update. \33[0m")
            return

        # progress bar
        playlist_bar = tqdm(
            playlists.items(),
            desc="Updating tags",
            unit="tracks",
            leave=self._verbose > 0,
            disable=self._verbose > 2 and self._verbose < 2, 
            file=sys.stdout,
        )

        load_errors = []
        save_errors = []
        count = 0

        for name, tracks in playlist_bar:
            for track in tracks:
                modified = False
                mod_image = False
                updating_tags = []
                # load file as mutagen object
                file_raw, ext = self.load_file(track["path"], **kwargs)
                if file_raw is None or file_raw == track["path"]:
                    load_errors.append(track["path"])
                    continue
                
                # get formatted dict of file's current metadata
                file_metadata, uri = self._extract(file_raw, ext)
                file_metadata = self._process(metadata=file_metadata, uri=uri, path=track["path"])

                # loop through each tag to process
                for tag_name in tags:
                    check_value = track[tag_name]  # for skip conditions
                    # get file type specific tag identifiers and new value
                    if tag_name == "uri" or tag_name == self._uri_tag:
                        if track["uri"] is False:
                            new_value = self._unavailable_uri_value
                            check_value = new_value
                        else:
                            new_value = track["uri"]
                        tag_name = self._uri_tag
                    elif tag_name == "track":  # add leading 0
                        new_value = f"0{track['track']}" if len(str(track['track'])) == 1 else track['track']
                    else:
                        new_value = track[tag_name]

                    tag_ids = self._tag_ids[ext].get(tag_name, [])
                    
                    # skip conditions
                    if tag_name != "image" and len(tag_ids) == 0:
                        # tag not in list of mapped tags
                        continue
                    elif tag_name == "bpm" and ext == '.m4a':
                        # m4a files can only save bpm to the nearest whole number
                        # compare as ints instead of floats and skip if equal
                        if file_metadata["bpm"] and check_value:
                            if int(file_metadata["bpm"]) == int(check_value):
                                continue
                    elif file_metadata[tag_name] == check_value:
                        continue

                    if not replace:
                        # don't desctructively replace tag
                        if tag_name == "image" and file_metadata["has_image"]:
                            # skip if file has embedded image
                            continue
                        elif tag_name == self._uri_tag:
                            if isinstance(file_metadata[tag_name], str) and self.check_spotify_valid(file_metadata[tag_name], kind=["uri"]):
                                # if uri tag exists in file and is a valid uri
                                continue
                        elif file_metadata[tag_name] != new_value and file_metadata[tag_name] not in ['', False, None, 0]:
                            # skip if tag is not empty
                            continue

                    # delete tags if there are multiple possible tag_ids for this tag
                    for tag in list(file_raw.tags).copy():
                        if any(t in tag for t in tag_ids):
                            modified = True
                            if not isinstance(tag, str):
                                tag = tag[0]
                            del file_raw[tag]
                            self._logger.debug(f"{track['path']} | Deleted tag from file: {tag} for {tag_name}")

                    if new_value is not None:
                        # file extension specific tag update and save updated file tags
                        # update 1st acceptable tag_id for this tag
                        tag_id = None if len(tag_ids) == 0 else tag_ids[0]
                        if tag_name == "image":
                            file_raw, mod_image = self.embed_image(file_raw, ext=ext, tag_id=tag_id, 
                                                                   image_url=new_value, **kwargs)
                            track["has_image"] = modified
                            modified = modified or mod_image
                        elif ext == ".flac":
                            file_raw[tag_id] = str(new_value)
                            modified = True
                        elif ext == ".mp3":
                            file_raw[tag_id] = getattr(mutagen.id3, tag_id)(3, text=str(new_value))
                            modified = True
                        elif ext == ".m4a":
                            if tag_name == "key":
                                file_raw[tag_id] = mutagen.mp4.MP4FreeForm(new_value.encode("utf-8"), 1)
                            elif tag_name == 'bpm':
                                file_raw[tag_id] = [int(new_value)]
                            else:
                                file_raw[tag_id] = [str(new_value)]
                            modified = True
                        elif ext == ".wma":
                            file_raw[tag_id] = mutagen.asf.ASFUnicodeAttribute(str(new_value))
                            modified = True
                        
                        if modified:
                            updating_tags.append(tag_name)

                try:  # try to save tags, skip if error and display path
                    if not dry_run and modified:
                        self._logger.debug(f"{track['path']} | Saving file with new tags: {updating_tags}")
                        file_raw.save()
                        count += 1
                    elif modified and self._verbose:
                        name = name if len(name) < 30 else name[:27] + '...'
                        title = file_metadata['title'] if len(file_metadata['title']) < 30 else file_metadata['title'][:27] + '...'
                        self._logger.debug(f"{name:<30} | {title:<30} | {'/'.join(updating_tags)}")
                        count += 1                  
                except mutagen.MutagenError:
                    save_errors.append(track["path"])

        if len(load_errors) > 0:
            print()
            load_errors = "\n".join(load_errors)
            self._logger.error(f"Could not load: \33[91m\n{load_errors} \33[0m")
        if len(save_errors) > 0:
            print()
            save_errors = "\n".join(save_errors)
            self._logger.error(f"Could not save: \33[91m\n{save_errors} \33[0m")

        logger = self._logger.info if self._verbose > 0 else self._logger.debug
        if not dry_run:
            logger(f"\33[92mDone | Modified {count} files for tags: {tags} \33[0m")
        else:
            logger(f"\33[92mDone | {count} files would have been modified for tags: {tags} \33[0m")

    def embed_image(self, file_raw, ext: str, image_url: str, tag_id: str = None, **kwargs) -> None:
        """
        Embed image to local files from given Spotify URI images.

        :param local: Mutagen file object
        :param ext: str. Extension of the file given
        :param image_url: str. URL of the image to embed
        :param tag_id: str. ID of the tag to update
        :return: Mutagen file object and bool (True if Mutagen file object modified)
        """
        if image_url is None:
            return file_raw, False

        try:  # open image from link
            img = urlopen(image_url)
        except URLError:
            self._logger.error(f"{image_url} | Failed to open image")
            return file_raw, False

        # file extension specific embedding
        if ext == '.mp3':
            file_raw[tag_id] = mutagen.id3.APIC(
                mime='image/jpeg',
                type=mutagen.id3.PictureType.COVER_FRONT,
                data=img.read()
            )
        elif ext == '.flac':
            image_obj = mutagen.flac.Picture()
            image_obj.type = mutagen.id3.PictureType.COVER_FRONT
            image_obj.mime = u"image/jpeg"
            image_obj.data = img.read()

            # replace embedded image
            file_raw.clear_pictures()
            file_raw.add_picture(image_obj)
        elif ext == '.m4a':
            file_raw[tag_id] = [
                mutagen.mp4.MP4Cover(img.read(), imageformat=mutagen.mp4.MP4Cover.FORMAT_JPEG)
            ]
        else:  # wma image embedding not possible
            img.close()
            file_raw[tag_id] = mutagen.asf._attrs.ASFByteArrayAttribute(data=img.read())
        
        img.close()
        return file_raw, True

    #############################################################
    ## Transform
    #############################################################       
    def convert_metadata(self, playlists: dict, key: str = "uri", fields: list = None, out: str = "dict", sort_keys: bool = False, reverse: bool = False, **kwargs):
        """
        Convert dict from <name>: <list of dicts of track's metadata> to simpler, sorted key-value pairs.

        :param playlists: dict. Metadata in form <name>: <list of dicts of track's metadata>
        :param key: str. Key from metadata dict to use as the key in the new dict.
        :param fields: str or list. Keys from metadata dict to use as the values in the new dict.
                        If None, keeps the whole metadata dict as the value.
        :param out: str, default="dict". Output type as dict or dict of lists of all
                                        available values. Can be "dict" or "list".
        :param sort_keys: bool, default=False. If returning a dict, sort on keys
        :param reverse: bool, default=False. If sort_keys is True, reverse sort order.
        :return: list or dict. [track metadata] OR <key>: [<value> OR <track metadata>]
        """
        if len(playlists) == 0:
            return {}
        
        if key is None and fields is None:  # return flat list of all values
            return [track for tracks in playlists.values() for track in tracks]
        
        converted = [] if key is None else {}
        # these parameter settings should just return the same dict as input
        if out == "list" and fields is None:
            return playlists
        
        fields = [fields] if isinstance(fields, str) else fields
        playlists = {None: playlists} if isinstance(playlists, list) else playlists

        for name, tracks in playlists.items():  # get list of track metadata for each group
            for track in tracks:
                if fields is None:
                    filtered = track
                elif len(fields) == 1 and fields[0] in track:
                    filtered = track[fields[0]]
                elif len(fields) > 1:
                    filtered = {field: track[field] for field in fields}
                
                tag_value = track.get(key)

                if key is None:
                    converted.append(filtered)
                elif key == "name":
                    converted[name] = converted.get(name, [])
                    converted[name].append(filtered)
                elif out == "tracks":
                    converted[tag_value] = converted.get(tag_value, [])
                    converted[tag_value].append(filtered)
                elif tag_value:  # if key found and valid
                    # add track to final dict with filtered values or dict of all metadata
                    if out == "dict":
                        converted[tag_value] = filtered
                    # save data needed to produce dict of lists, sorted by path
                    elif out == "list":
                        converted[tag_value] = converted.get(tag_value, {})
                        converted[tag_value][track["path"]] = track[fields[0]]


        if isinstance(converted, dict):
            if out == "list":  # sort lists by path
                for k, v in converted.items():
                    converted[k] = [v for _, v in sorted(v.items())]
            
            if sort_keys:
                if key in ["date_added", "date_modified", "last_played"]:
                    sort_key = lambda key: self._str_ts_to_int(key[0])
                else:
                    sort_key = lambda key: self._strip_ignore_words(key[0])
                return dict(sorted(converted.items(), key=sort_key, reverse=reverse))
        
        return converted
        

    def modify_compilation_tags(
            self, local: dict, compilation_check: bool = True, **kwargs) -> dict:
        """
        Determine if album is compilation and modify metadata:
        - Set compilation to 1
        - Set track number in ascending order by filename
        - Set disc number to 1
        - Set album name to folder name
        - Set album artist to 'Various'

        :param local: dict. <name>: <list of dicts of local track's metadata>.
        :param compilation_check: bool, default=True. If True, determine compilation for each album.
            If False, treat all albums as compilation.
        :return: Modified albums <name>: <list of dicts of local track's metadata>.
        """
        print()
        self._logger.info(
            f"\33[1;95m -> \33[1;97mSetting compilation style tags for {len(local)} albums \33[0m")
        self._logger.debug(f"Compilation check: {compilation_check}")

        modified = {}
        count = 0
        for name, tracks in local.items():
            # check if compilation
            compilation = self.check_compilation(tracks) if compilation_check else True

            if compilation:
                # determine order of tracks by filename
                track_order = sorted(basename(track['path']) for track in tracks)

                for track in tracks:  # set tags
                    track["compilation"] = 1
                    track['track'] = track_order.index(basename(track['path'])) + 1
                    track["disc"] = 1
                    track["album"] = track["folder"]
                    track["album_artist"] = "Various"
                    count += 1

                modified[name] = tracks
            else:
                for track in tracks:  # set tags
                    track["compilation"] = 0
                    count += 1

        logger = self._logger.info if self._verbose > 0 else self._logger.debug
        logger(f"\33[92mDone | Set metadata for {count} tracks \33[0m")
        return modified

    def filter_tracks(self, playlists: dict, filter_tags: dict = None, **kwargs) -> dict:
        """
        Filter tracks to only those with a valid uri and not including a tag in <filter_tags>.

        :param playlists: dict. Local playlists in form <name>: <list of dicts of track's metadata>
        :param filter_tags: dict, default=None. <tag name>: <list of tags to filter out>. If None, skip this filter
        :return: dict. Filtered playlists.
        """
        self._logger.debug(
            f"Filtering tracks in {len(playlists)} playlists | "
            f"Filter out tags: {filter_tags}"
        )

        # for appropriately aligned formatting
        max_width = len(max(playlists, key=len)) + 1 if len(max(playlists, key=len)) + 1 < 50 else 50

        filtered = {}
        for name, tracks in playlists.items():
            # list of all valid tracks to add
            tracks = [track for track in tracks if isinstance(track['uri'], str)]
            filtered[name] = tracks

            if filter_tags is not None and len(filter_tags) > 0:
                # filter out tracks with tags in filter param
                filtered[name] = []
                for track in tracks:
                    for tag, values in filter_tags.items():
                        if isinstance(track[tag], str) and all(isinstance(v, str) for v in values):
                            # string processing
                            tag_value = track[tag].strip().lower()
                            values = [v.strip().lower() for v in values]

                            if all(v not in tag_value for v in values):
                                filtered[name].append(track)
                            

            self._logger.debug(
                f"{name if len(name) < 50 else name[:47] + '...':<{max_width}} | "
                f"Filtered out {len(tracks) - len(filtered[name]):>3} tracks"
            )
        return filtered

    #############################################################
    ## Extract Images
    #############################################################
    def extract_images(self, playlists: dict, dim: bool = True, **kwargs) -> str:
        """
        Extract and save all embedded images from local files or Spotify tracks.

        :param playlists: dict. <parent folder name>: <list of dicts of track's metadata>
        :param dim: bool, default=True. Add dimensions to image filenames on export as suffix in parentheses.
        :return: str. Parent folder path of the exported images
        """
        # determine kind of data input and save folder
        kind = "local" if "has_image" in list(playlists.values())[0][0] else "spotify"
        save_folder = join(self._data_path, f'images_{kind}')

        tracks_len = len([t for tracks in playlists.values() for t in tracks])

        print()
        self._logger.info(
            f"\33[1;95m -> \33[1;97mExtracting images for {tracks_len} tracks to {save_folder} \33[0m")

        playlist_bar = tqdm(
            playlists.items(),
            desc='Extracting images',
            unit='folders',
            leave=self._verbose > 0,
            disable=self._verbose > 2 and self._verbose < 2, 
            file=sys.stdout)
        count = 0

        for name, tracks in playlist_bar:
            count_current = 0

            track_bar = tracks
            if len(track_bar) > 20:  # show progress bar for large # of tracks
                track_bar = tqdm(
                    track_bar,
                    desc=name,
                    unit="tracks",
                    leave=False,
                    file=sys.stdout,
                )

            for track in track_bar:
                if kind == "local":
                    img = self.get_local_image_bytes(track, **kwargs)
                    img = Image.open(BytesIO(img))

                    # define save path for this track's image
                    save_path = join(save_folder, name, splitext(basename(track['path']))[0])
                elif kind == "spotify":
                    try:  # open image from link
                        img = Image.open(BytesIO(urlopen(track['image']).read()))
                    except URLError:
                        self._logger.error(
                            f"{track['title']} | Failed to open image from {track['image']}")
                        continue

                    # define save path for this track's image, adding leading 0 to filename
                    title = re.sub(r'[\\/*?:"<>|]', '', track['title'])
                    i = track['position'] if track["position"] is not None else track['track']
                    i = f"0{i}" if len(str(i)) == 1 else i
                    filename = f"{i} - {title}"

                    # sanitise playlist name for folder name
                    name = re.sub(r'[\\/*?:"<>|]', '', name)
                    save_path = join(save_folder, name, filename)

                # if no image found, skip
                if img is None:
                    continue

                # create save folder for this track if doesn't exist
                if not exists(split(save_path)[0]):
                    os.makedirs(split(save_path)[0])

                # load image and determine embedded image file type
                img_ext = '.png' if 'png' in img.format.lower() else '.jpg'

                # add dimensions to filename if set and save
                save_path += f" ({'x'.join(str(n) for n in img.size)})" if dim else ''
                img.save(save_path + img_ext)

                count_current += 1

            count += count_current

        logger = self._logger.info if self._verbose > 0 else self._logger.debug
        logger(f"Extracted {count} images to {save_folder}")
        return save_folder

    def get_local_image_bytes(self, track: dict, **kwargs) -> str:
        """
        Extract bytes data for image in locally stored track.

        :param track: dict. Track metadata including 'path' key
        :return: str. Bytes string of the image.
        """
        # load file as mutagen object
        raw_data, ext = self.load_file(track, **kwargs)
        if raw_data is None or raw_data == track["path"]:
            return None

        # extension specific processing
        img = None
        if ext == '.flac':
            if len(raw_data.pictures) > 0:
                img = raw_data.pictures[0].data
        else:
            for file_tag in raw_data:
                tags = self._tag_ids[ext].get("image", [])
                for tag in tags:
                    if tag in file_tag and not img:
                        if '.mp3' in ext:
                            img = raw_data[file_tag].data
                        elif '.m4a' in ext:
                            img = bytes(raw_data[file_tag][0])
                        elif '.wma' in ext:
                            img = raw_data[file_tag][0].value
                        break

        return img
