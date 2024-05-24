import asyncio

from p3 import *

asyncio.run(load_objects(spotify_api))
asyncio.run(load_library(spotify_api))
asyncio.run(update_playlist(spotify_api))
