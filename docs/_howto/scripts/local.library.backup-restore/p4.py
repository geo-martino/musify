from p3 import *

results = library.save_tracks(replace=True, dry_run=False)
# ... or if tags were specified
results = library.save_tracks(tags=tags, replace=True, dry_run=False)

library.log_save_tracks_result(results)
