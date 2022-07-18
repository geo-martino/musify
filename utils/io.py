import json
import os
from os.path import basename, dirname, exists, join, splitext, normpath

from time import sleep


class IO:

    def save_json(self, data: dict, filename: str, parent: bool=False, no_output: bool=False, **kwargs) -> None:
        """
        Save dict to json file in data path.

        :param data: dict. Data to save.
        :param filename: str. Filename to save under.
        :param parent: bool, default=False. Use parent folder of data path.
        :param no_output: bool, default=False. Don't save the file.
        """
        if no_output and not parent:
            # skip if no output set and not saving to parent folder
            return False
        
        # get filepath and save
        if not filename.lower().endswith(".json"):
            filename += ".json"
        json_path = dirname(self.DATA_PATH) if parent else self.DATA_PATH
        json_path = join(json_path, normpath(filename))
        self._logger.debug(f"Saving {json_path}")

        with open(json_path, "w", encoding='utf8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    def load_json(self, filename: str, parent: bool=False, **kwargs) -> dict:
        """
        Load json from data path.

        :param filename: str. Filename to load from.
        :param parent: bool, default=False. Use parent folder of data path.
        :return: Loaded JSON object, or False if not found. 
        """
        # get filepath and load
        if not filename.lower().endswith(".json"):
            filename += ".json"
        json_path = dirname(self.DATA_PATH) if parent else self.DATA_PATH
        json_path = join(json_path, normpath(filename))
        
        if exists(json_path):
            self._logger.debug(f"Loading: {json_path}")
            with open(json_path, "r", encoding='utf8') as f:
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

    def delete_json(self, filename: str, parent: bool=False, **kwargs) -> dict:
        """
        Delete json file at for given filename.

        :param filename: str. Filename to process.
        :param parent: bool, default=False. Use parent folder of data path.
        :return: Path to file that was deleted, or False if failed.
        """
        # get filepath and load
        if not filename.lower().endswith(".json"):
            filename += ".json"
        json_path = dirname(self.DATA_PATH) if parent else self.DATA_PATH
        json_path = join(json_path, normpath(filename))
        

        if exists(json_path):
            self._logger.debug(f"Deleting: {json_path}")
            os.remove(json_path)
        else:
            return False

        return json_path