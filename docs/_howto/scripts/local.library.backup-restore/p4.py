from p3 import *

import asyncio

results = asyncio.run(library.save_tracks(replace=True, dry_run=False))
# ... or if tags were specified
results = asyncio.run(library.save_tracks(tags=tags, replace=True, dry_run=False))

library.log_save_tracks_result(results)
