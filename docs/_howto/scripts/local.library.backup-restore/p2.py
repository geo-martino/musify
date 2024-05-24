from p1 import *

with open(path, "r") as file:
    backup = json.load(file)

library.restore_tracks(backup["tracks"])
