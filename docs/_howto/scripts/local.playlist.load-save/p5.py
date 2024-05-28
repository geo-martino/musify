from p4 import *

result = asyncio.run(playlist.save(dry_run=False))
print(result)
