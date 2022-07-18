import os
import re
import sys
from io import BytesIO
from os.path import basename, exists, join, split, splitext, dirname
from urllib.error import URLError
from urllib.request import urlopen

import mutagen
from PIL import Image
from tqdm.auto import tqdm


class Process():

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

        tracks_len = len([t for tracks in playlists.values() for t in tracks])
        print()
        self._logger.info(
            f"\33[1;95m -> \33[1;97mUpdating tags in {tracks_len} files: {tags}\33[0m")

        tags = [t for t in tags if t != 'image']

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
            for md_input in tracks:
                modified = False
                # load file as mutagen object
                md_file, ext = self.load_file(md_input["path"], **kwargs)
                if md_file is None or md_file == md_input["path"]:
                    load_errors.append(md_input["path"])
                    continue

                # loop through each tag to process
                for tag_name in tags:
                    # get file type specific tag identifiers and new value
                    if tag_name == "uri" or tag_name == self._uri_tag:
                        tag_ids = self._tag_ids[ext].get(self._uri_tag, [])
                        new_value = md_input["uri"]
                    else:
                        tag_ids = self._tag_ids[ext].get(tag_name, [])
                        new_value = md_input[tag_name]

                    if tag_name == "compilation":
                        md_input[tag_name] = int(md_input[tag_name])

                    # skip conditions
                    if len(tag_ids) == 0:
                        # tag not in list of mapped tags
                        continue
                    elif not replace and any(t in f for f in md_file for t in tag_ids):
                        # do not descrtuctively replace if exists and refresh is False
                        continue

                    # delete tags if there are multiple possible _tag_ids for this tag
                    if len(tag_ids) > 1 or new_value is None:
                        clear = []

                        # produce list of tags to be deleted
                        for tag_id in tag_ids:
                            for tag_file in md_file:
                                if tag_id in tag_file:
                                    clear.append(tag_file)
                        for tag_file in clear:  # delete tag
                            del md_file[tag_file]
                            modified = True

                    if new_value is not None:
                        modified = True
                        # URI tag handling
                        if tag_name == "uri" or tag_name == self._uri_tag:
                            if md_input['uri'] is False:
                                # placeholder URI for unavailable songs
                                new_value = self._unavailable_uri_value

                        # file extension specific tag update and save updated file tags
                        tag_id = tag_ids[0]  # update 1st acceptable tag_id for this tag
                        if ext == ".flac":
                            md_file[tag_id] = str(new_value)
                        elif ext == ".mp3":
                            md_file[tag_id] = getattr(mutagen.id3, tag_id)(3, text=str(new_value))
                        elif ext == ".m4a":
                            if tag_name != "bpm":  # TODO: how to update bpm tag on m4a
                                md_file[tag_id] = [str(new_value)]
                        elif ext == ".wma":
                            md_file[tag_id] = mutagen.asf.ASFUnicodeAttribute(str(new_value))

                try:  # try to save tags, skip if error and display path
                    if not dry_run and modified:
                        md_file.save()
                        count += 1
                except mutagen.MutagenError:
                    save_errors.append(md_input["path"])

        if len(load_errors) > 0:
            load_errors = "\n".join(load_errors)
            self._logger.error(f"Could not load: \33[91m\n{load_errors}\33[0m")
        if len(save_errors) > 0:
            save_errors = "\n".join(save_errors)
            self._logger.error(f"Could not save: \33[91m\n{save_errors}\33[0m")

        logger = self._logger.info if self._verbose else self._logger.debug
        logger(f"\33[92mDone | Modified {count} files for tags: {tags}\33[0m")

    #############################################################
    # Transform
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

        :param local: dict. <name>: <list of dicts of local track's metadata>.
        :param compilation_check: bool, default=True. If True, determine compilation for each album.
            If False, treat all albums as compilation.
        :return: Modified albums <name>: <list of dicts of local track's metadata>.
        """
        print()
        self._logger.info(
            f"\33[1;95m -> \33[1;97mSetting compilation style tags for {len(local)} albums\33[0m")
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
                    count += 1

                modified[name] = tracks
            else:
                for track in tracks:  # set tags
                    track["compilation"] = 0
                    count += 1

        logger = self._logger.info if self._verbose else self._logger.debug
        logger(f"\33[92mDone | Set metadata for {count} tracks\33[0m")
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
        max_width = len(max(playlists, key=len))

        filtered = {}
        for name, tracks in playlists.items():
            # list of all valid tracks to add
            tracks = [track for track in tracks if isinstance(track['uri'], str)]
            filtered[name] = tracks

            if filter_tags is not None:
                # filter out tracks with tags in filter param
                filtered[name] = []
                for track in tracks:
                    for tag, values in filter_tags.items():
                        if isinstance(track[tag], str) and all(isinstance(v, str) for v in values):
                            # string processing
                            tag_value = track[tag].strip().lower()
                            values = [v.strip().lower() for v in values]

                        if not any(tag_value == v for v in values):
                            filtered[name].append(track)

            self._logger.debug(
                f"{name:<{len(name) + max_width - len(name)}} | "
                f"Filtered out {len(tracks) - len(filtered[name]):>3} tracks"
            )
        return filtered

    #############################################################
    # Images
    #############################################################
    def embed_images(self, local: dict, spotify: dict, replace: bool = False,
                     dry_run: bool = True, **kwargs) -> None:
        """
        Embed images to local files from linked Spotify URI images.
        WARNING: This function can destructively modify your files.

        :param local: dict. <name>: <list of dicts of local track's metadata>.
        :param spotify: dict. <uri>: <dict of spotify track's metadata>
        :param replace: bool, default=False. Replace locally embedded images if True.
            Otherwise, only add images to files with no embedded image.
        :param dry_run: bool, default=False. Run function, but do not modify file at all.
        """
        if len(local) == 0:  # return if no local files given
            return

        # convert playlists to URI as key
        local = self.convert_metadata(local, key="uri", **kwargs)

        print()
        self._logger.info(
            f"\33[1;95m -> \33[1;97mEmbedding images from Spotify for {len(local)} files\33[0m")

        # progress bar
        local_bar = tqdm(
            local.items(),
            desc='Embedding images',
            unit='tracks',
            leave=self._verbose,
            file=sys.stdout)
        count = 0

        for uri, track in local_bar:
            modified = False
            # skip if not replacing embedded images
            if uri not in spotify or (not replace and track['has_image']):
                continue

            # load file as mutagen object
            raw_data, ext = self.load_file(track, **kwargs)
            if not raw_data or not ext:
                continue

            try:  # open image from link
                img = urlopen(spotify[uri]['image'])
            except URLError:
                self._logger.error(f"{track['title']} | Failed to open image from {track['image']}")
                continue

            # delete all embedded images
            for tag in dict(raw_data.tags).copy():
                if dry_run or ext == '.wma':
                    # TODO: remove '.wma' bit after coding embed image to wma below
                    break
                elif any(t in tag for t in self._tag_ids[ext].get("image", [])):
                    modified = True
                    del raw_data[tag]

            # file extension specific embedding
            if ext == '.mp3':
                raw_data['APIC'] = mutagen.id3.APIC(
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
                raw_data.clear_pictures()
                raw_data.add_picture(image_obj)
            elif ext == '.m4a':
                raw_data["covr"] = [
                    mutagen.mp4.MP4Cover(img.read(), imageformat=mutagen.mp4.MP4Cover.FORMAT_JPEG)
                ]
            elif ext == '.wma':  # TODO: embed image to wma
                img.close()
                continue
            else:
                continue

            # close link and save updated file tags
            if not dry_run and modified:
                raw_data.save()
                count += 1
            img.close()

            track["has_image"] = modified

        logger = self._logger.info if self._verbose else self._logger.debug
        logger(f"\33[92mDone | Modified images for {count} files\33[0m")

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
            f"\33[1;95m -> \33[1;97mExtracting images for {tracks_len} tracks to {save_folder}\33[0m")

        playlist_bar = tqdm(
            playlists.items(),
            desc='Extracting images',
            unit='folders',
            leave=self._verbose,
            file=sys.stdout)
        count = 0

        for name, tracks in playlist_bar:
            count_current = 0

            for track in tracks:
                if kind == "local":
                    img = self.get_local_image_bytes(track, **kwargs)

                    # define save path for this track's image
                    save_path = join(save_folder, name, splitext(basename(track['path']))[0], )
                elif kind == "spotify":
                    try:  # open image from link
                        img = Image.open(BytesIO(urlopen(track['image']).read()))
                    except URLError:
                        self._logger.error(
                            f"{track['title']} | Failed to open image from {track['image']}")
                        continue

                    # define save path for this track's image
                    title = re.sub(r'[\\/*?:"<>|]', '', track['title'])
                    if track["position"] is not None:
                        filename = f"{track['position']} - {title}"
                    else:
                        filename = f"{track['track']} - {title}"
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
                img = Image.open(BytesIO(img))
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
