from p3 import *

import asyncio

asyncio.run(load_objects(api))
asyncio.run(update_playlist("<YOUR PLAYLIST'S NAME>", api))  # case sensitive
