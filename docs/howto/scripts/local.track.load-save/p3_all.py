from p2 import *

results = asyncio.run(track.save(replace=True, dry_run=False))

# print a list of the tags that were saved
print([tag.name for tag in results.updated])
