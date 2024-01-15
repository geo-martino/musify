from os.path import basename, dirname

PROGRAM_NAME = "Musify"
__version__ = "0.3.0"
PROGRAM_OWNER_NAME = "George Martin Marino"
PROGRAM_OWNER_USER = "geo-martino"
PROGRAM_OWNER_EMAIL = f"gm.engineer+{PROGRAM_NAME.lower()}@pm.me"
PROGRAM_URL = f"https://github.com/{PROGRAM_OWNER_USER}/{PROGRAM_NAME.lower()}"

MODULE_ROOT: str = basename(dirname(__file__))
PACKAGE_ROOT: str = dirname(dirname(dirname(__file__)))
