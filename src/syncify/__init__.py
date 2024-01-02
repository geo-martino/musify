from os.path import basename, dirname

PROGRAM_NAME = "Syncify"
__version__ = "0.3"
PROGRAM_OWNER_NAME = "geo-martino"
PROGRAM_OWNER_EMAIL = f"gm.engineer+{PROGRAM_NAME.lower()}@pm.me"
PROGRAM_URL = f"https://github.com/{PROGRAM_OWNER_NAME}/{PROGRAM_NAME.casefold()}"

MODULE_ROOT: str = basename(dirname(__file__))
PACKAGE_ROOT: str = dirname(dirname(dirname(__file__)))
