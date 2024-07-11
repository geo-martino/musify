from p1 import *

from musify.libraries.local.track import load_track

track = asyncio.run(load_track("<PATH TO A TRACK>"))
