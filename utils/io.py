import io
import json
import os
from os.path import basename, dirname, exists, join, normpath, splitext
from time import sleep

import xmltodict
from lxml import etree


class IO:

    def save_json(self, data: dict, filename: str, parent: bool = False,
                  no_output: bool = False, **kwargs) -> None:
        """
        Save dict to json file in data path.

        :param data: dict. Data to save.
        :param filename: str. Filename to save under.
        :param parent: bool, default=False. Use parent folder of data path.
        :param no_output: bool, default=True. Suppress output if True.
        """
        if no_output and not parent:
            # skip if no output set and not saving to parent folder
            return False
        
        # get filepath and save
        if not filename.lower().endswith(".json"):
            filename += ".json"
        json_path = dirname(self._data_path) if parent else self._data_path
        json_path = join(json_path, normpath(filename))

        if not exists(dirname(json_path)):
            os.makedirs(dirname(json_path))
        
        self._logger.debug(f"Saving: {json_path}")
        with open(json_path, "w", encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    def load_json(self, filename: str, parent: bool = False, **kwargs) -> dict:
        """
        Load json from data path.

        :param filename: str. Filename to load from.
        :param parent: bool, default=False. Use parent folder of data path.
        :return: Loaded JSON object, or False if not found.
        """
        # get filepath and load
        if not filename.lower().endswith(".json"):
            filename += ".json"
        json_path = dirname(self._data_path) if parent else self._data_path
        json_path = join(json_path, normpath(filename))

        if exists(json_path):
            self._logger.debug(f"Loading: {json_path}")
            with open(json_path, "r", encoding='utf-8') as f:
                return json.load(f)
        else:
            self._logger.debug(f"{json_path} not found")
            return False

    def update_json(self, data, filename: str, **kwargs) -> dict:
        """
        Update json from data path with new data.

        :param data: list/dict. Data to update file with.
        :param filename: str. Filename to process.
        :return: Updated JSON object, or False if failed.
        """
        # get filepath and load
        self._logger.debug(f"Updating: {filename}")
        loaded = self.load_json(filename, **kwargs)
        if not loaded:
            self.save_json(data, filename, **kwargs)
            return data

        try:
            if isinstance(loaded, dict):
                if isinstance(list(loaded.values())[0], dict):
                    for k, v in data.items():
                        if k in loaded:
                            loaded[k].update(v)
                        else:
                            loaded[k] = v
                else:
                    loaded.update(data)
            elif isinstance(loaded, list):
                loaded.extend(data)
        except (AttributeError, ValueError):
            self._logger.error(f"{filename} update failed, skipping...")
            return False

        self.save_json(loaded, filename, **kwargs)
        return loaded

    def delete_json(self, filename: str, parent: bool = False, **kwargs) -> dict:
        """
        Delete json file at for given filename.

        :param filename: str. Filename to process.
        :param parent: bool, default=False. Use parent folder of data path.
        :return: Path to file that was deleted, or False if failed.
        """
        # get filepath and load
        if not filename.lower().endswith(".json"):
            filename += ".json"
        json_path = dirname(self._data_path) if parent else self._data_path
        json_path = join(json_path, normpath(filename))

        if exists(json_path):
            self._logger.debug(f"Deleting: {json_path}")
            os.remove(json_path)
        else:
            return False

        return json_path

    def save_m3u(self, data: dict, filename: str, dry_run: bool=True, append_path: bool=True, **kwargs) -> list:
        """
        Save list of paths to playlists folder with m3u extension.

        :param data: dict. Data to save.
        :param filename: str. Filename to process.
        :param dry_run: bool, default=True. Suppress output if True.
        :param append_path: bool, default=True. Append default playlists path to filename.
        """
        # get filepath and save
        filename = normpath(filename)
        if not filename.lower().endswith(".m3u"):
            filename += ".m3u"
        m3u_path = join(self._playlists_path, filename) if append_path else filename

        if not dry_run:
            if not exists(dirname(m3u_path)):
                os.makedirs(dirname(m3u_path))

            self._logger.debug(f"Saving {len(data)} tracks: {m3u_path}")
            with open(m3u_path, 'w', encoding='utf-8') as f:
                f.writelines([t.strip() + '\n' for t in data])

    def load_m3u(self, m3u_path: str, **kwargs) -> list:
        """
        Load m3u playlist from playlists folder to a list a paths.

        :param m3u_path: str. Path to process.
        :return: list.
        """ 
        if exists(m3u_path):
            self._logger.debug(f"Loading: {m3u_path}")
            with open(m3u_path, "r", encoding='utf-8') as f:
                return [line.rstrip() for line in f]
        else:
            self._logger.debug(f"{m3u_path} not found")
            return False

    def save_autoplaylist(self, data: dict, filename: str, dry_run: bool=True, append_path: bool=True, **kwargs) -> dict:
        """
        Save dict representing xml like object to playlists folder with xautopf extension.

        :param data: dict. Data to save.
        :param filename: str. Filename to process.
        :param dry_run: bool, default=True. Suppress output if True.
        :param append_path: bool, default=True. Append default playlists path to filename.
        """
        # get filepath and save
        if not filename.lower().endswith(".xautopf"):
            filename += ".xautopf"
        xml_path = join(self._playlists_path, normpath(filename)) if append_path else filename

        if not dry_run:
            if not exists(dirname(xml_path)):
                os.makedirs(dirname(xml_path))
            
            self._logger.debug(f"Saving: {xml_path}")
            with open(xml_path, 'w', encoding='utf-8') as f:
                f.write(xmltodict.unparse(data, pretty=True, short_empty_elements=True).replace('/>', ' />').replace('\t', '  '))

    def load_autoplaylist(self, xml_path: str, **kwargs) -> dict:
        """
        Load xml like object from playlists folder with xautopf extension to dict.

        :param xml_path: str. Path to process.
        :return: dict.
        """ 
        if exists(xml_path):
            self._logger.debug(f"Loading: {xml_path}")
            with open(xml_path, "r", encoding='utf-8') as f:
                return xmltodict.parse(f.read())
        else:
            self._logger.debug(f"{xml_path} not found")
            return False

    def load_xml(self, path: str, **kwargs) -> dict:
        """
        Load xml like object from path.

        :param path: str. Full path to file with extension.
        :return: dict.
        """ 
        raw = {}
        # get filepath and load
        if exists(path):
            self._logger.debug(f"Loading: {path}")
            for record in ReadXmlLibrary(path):
                for key, value in record.items():
                    raw[key] = value
            return raw
        else:
            self._logger.debug(f"{path} not found")
            return False
       

class ReadXmlLibrary:
    def __init__(self, fh):
        """
        Initialize 'iterparse' to generate 'start' and 'end' events on all tags

        :param fh: File Handle from the XML File to parse
        """
        self.context = etree.iterparse(fh, events=("start", "end",))

    def _parse(self):
        """
        Yield only at 'end' event, except 'start' from tag 'dict'
        :return: yield current Element
        """
        for event, elem in self.context:
            if elem.tag == 'plist' or \
                    (event == 'start' and not elem.tag == 'dict'):
                continue
            yield elem

    def _parse_key_value(self, key=None):
        _dict = {}
        for elem in self._parse():
            if elem.tag == 'key':
                key = elem.text
                continue

            if elem.tag in ['integer', 'string', 'date']:
                if not key is None:
                    _dict[key] = elem.text
                    key = None
                else:
                    print('Missing key for value {}'.format(elem.text))

            elif elem.tag in ['true', 'false']:
                _dict[key] = elem.tag == 'true'

            elif elem.tag == 'dict':
                if not key is None:
                    _dict[key] = self._parse_dict(key)
                    key = None
                else:
                    return elem, _dict
            else:
                pass
                # print('Unknown tag {}'.format(elem.tag))

    def _parse_dict(self, key=None):
        elem = next(self._parse())
        elem, _dict = self._parse_key_value(elem.text)
        return _dict

    def __iter__(self):
        for elem in self._parse():
            if elem.tag == 'dict':
                try:
                    yield self._parse_dict()
                except StopIteration:
                    return
            else:
                pass
                # print('Unknown tag {}'.format(elem.tag))
