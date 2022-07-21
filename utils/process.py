import os
import re
import sys
from io import BytesIO
from os.path import basename, dirname, exists, join, split, splitext
from urllib.error import URLError
from urllib.request import urlopen

import json
from time import sleep

import mutagen
from PIL import Image
from tqdm.auto import tqdm


class Process():

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
        :param dry_run: bool, default=False. Run function, but do not modify file at all.
        """
        if tags is None:
            return

        tracks_all = [t for tracks in playlists.values() for t in tracks]
        print()
        self._logger.info(
            f"\33[1;95m -> \33[1;97mUpdating tags in {len(tracks_all)} files: {tags} \33[0m")

        # progress bar
        playlist_bar = tqdm(
            playlists.items(),
            desc="Updating tags",
            unit="tracks",
            leave=self._verbose,
            file=sys.stdout,
        )

        load_errors = []
        save_errors = []
        count = 0

        for name, tracks in playlist_bar:
            for track in tracks:
                modified = False
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
                    # get file type specific tag identifiers and new value
                    if tag_name == "uri" or tag_name == self._uri_tag:
                        if track["uri"] is False:
                            new_value = self._unavailable_uri_value
                        else:
                            new_value = track["uri"]
                        tag_name = self._uri_tag
                    elif tag_name == "track":  # add leading 0
                        new_value = f"0{track['track']}" if len(str(track['track'])) == 1 else track['track']
                    else:
                        new_value = track[tag_name]
                    
                    tag_ids = self._tag_ids[ext].get(tag_name, [])

                    # skip conditions
                    if len(tag_ids) == 0:
                        # tag not in list of mapped tags
                        continue
                    elif file_metadata[tag_name] == new_value:
                        # skip needlessly updating tags if they are the same
                        continue
                    elif new_value == self._unavailable_uri_value and not file_metadata["uri"]:
                        # same again but for unavailable uris
                        continue
                    elif tag_name == self._uri_tag and file_metadata["uri"] == new_value:
                        # same again but solves an issue with some malformed,
                        # and persistent comment tags on mp3 files
                        continue
                    elif tag_name == "bpm" and file_metadata["bpm"] and new_value:
                        if int(file_metadata["bpm"]) == int(new_value):
                            # m4a files can only save bpm to the nearest whole number
                            # compare as ints instead of floats and skip if equal
                            continue
                    elif tag_name == "track" and file_metadata["track"] == track["track"]:
                        # handle same track numbers
                        continue
                    elif tag_name == "image" and not replace and file_metadata["has_image"]:
                        # don't desctructively replace embedded images if exists and refresh is False
                        continue
                    elif not replace and any(t in f for f in file_raw for t in tag_ids):
                        # don't descrtuctively replace if exists and refresh is False 
                        if tag_name != self._uri_tag:
                            # and not uri tag. Force replaces tag with new uri
                            continue

                    # delete tags if there are multiple possible tag_ids for this tag
                    for tag in list(file_raw.tags).copy():
                        if any(t in tag for t in tag_ids):
                            modified = True
                            if not isinstance(tag, str):
                                tag = tag[0]
                            del file_raw[tag]

                    if new_value is not None:
                        # file extension specific tag update and save updated file tags
                        tag_id = tag_ids[0]  # update 1st acceptable tag_id for this tag
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

                try:  # try to save tags, skip if error and display path
                    if not dry_run and modified:
                        file_raw.save()
                        count += 1
                    elif modified and self._verbose and replace:
                        tag_changes = " | ".join(t for t in tags if track[t] != file_metadata[t])
                        name = name if len(name) < 30 else name[:27] + '...'
                        title = file_metadata['title'] if len(file_metadata['title']) < 30 else file_metadata['title'][:27] + '...'
                        self._logger.info(f" {name:<30} : {title:<30} | {tag_changes}") 
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

        logger = self._logger.info if self._verbose else self._logger.debug
        if not dry_run:
            logger(f"\33[92mDone | Modified {count} files for tags: {tags} \33[0m")
        else:
            logger(f"\33[92mDone | {count} files will be modified with '-x' flag for tags: {tags} \33[0m")

    def embed_image(self, file_raw, ext: str, tag_id: str, image_url: str, **kwargs) -> None:
        """
        Embed image to local files from given Spotify URI images.

        :param local: Mutagen file object
        :param ext: str. Extension of the file given
        :param tag_id: str. ID of the tag to update
        :param image_url: str. URL of the image to embed
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
    def convert_metadata(self, playlists: dict, key: str = "uri",
                         value: str = None, out: str = "dict", **kwargs) -> dict:
        """
        Convert dict from <name>: <list of dicts of track's metadata> to simpler, sorted key-value pairs.

        :param playlists: dict. Metadata in form <name>: <list of dicts of track's metadata>
        :param key: str. Key from metadata dict to use as the key in the new dict.
        :param value: str. Value from metadata dict to use as the value in the new dict.
                        If None, keeps the whole metadata dict as the value.
        :param out: str, default="dict". Output type as dict or dict of lists of all
                                        available values. Can be "dict" or "list".
        :return: dict. <key>: <value> OR <track metadata>
        """
        converted = {}
        # these parameter _settings should just return the same dict as input
        if out == "list" and value is None:
            return playlists

        for name, tracks in playlists.items():  # get list of track metadata for each group
            if key == "name" and value is not None:
                converted[name] = [track[value] for track in tracks]
                continue
        
            for track in tracks:
                if track.get(key):  # if key found and valid
                    # add track to final dict with specified value or dict of all metadata
                    if out == "dict":
                        if value is None:
                            converted[track[key]] = track
                        elif value in track:
                            converted[track[key]] = track[value]
                    # save data needed to produce dict of lists, sorted by path
                    elif out == "list" and value in track:
                        converted[track[key]] = converted.get(track[key], {})
                        converted[track[key]][track["path"]] = track[value]

        if out == "list":  # sort lists by path
            for k, v in converted.items():
                converted[k] = [v for _, v in sorted(v.items())]

        return dict(sorted(converted.items()))

    def modify_compilation_tags(
            self, local: dict, compilation_check: bool = True, **kwargs) -> dict:
        """
        Determine if album is compilation and modify metadata:
        - Set all compilation ags to true
        - Set track number in ascending order by filename
        - Set disc number to None
        - Set album name to folder name

        :param local: dict. <name>: <list of dicts of local track's metadata>.
        :param compilation_check: bool, default=True. If True, determine compilation for each album.
            If False, treat all albums as compilation.
        :return: Modified albums <name>: <list of dicts of local track's metadata>.
        """
        print()
        self._logger.info(
            f"\33[1;95m -> \33[1;97mSetting compilation style tags for {len(local)} albums \33[0m")
        self._logger.debug(f"Compilation check: {compilation_check}")

        import json

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
                    track["disc"] = None
                    track["album"] = track["folder"]
                    track["album_artist"] = "Various"
                    count += 1

                modified[name] = tracks
            else:
                for track in tracks:  # set tags
                    track["compilation"] = 0
                    count += 1

        logger = self._logger.info if self._verbose else self._logger.debug
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
        max_width = len(max(playlists, key=len)) if len(max(playlists, key=len)) < 50 else 50

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

                            if all(tag_value != v for v in values):
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
        save_folder = join(self.DATA_PATH, f'images_{kind}')

        tracks_len = len([t for tracks in playlists.values() for t in tracks])

        print()
        self._logger.info(
            f"\33[1;95m -> \33[1;97mExtracting images for {tracks_len} tracks to {save_folder} \33[0m")

        playlist_bar = tqdm(
            playlists.items(),
            desc='Extracting images',
            unit='folders',
            leave=self._verbose,
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

        logger = self._logger.info if self._verbose else self._logger.debug
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
