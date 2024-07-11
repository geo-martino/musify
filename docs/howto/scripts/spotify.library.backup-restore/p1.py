from p0 import *

import json

path = "remote_backup.json"
with open(path, "w") as file:
    json.dump(library.json(), file, indent=2)
