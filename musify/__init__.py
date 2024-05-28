"""Welcome to Musify"""
from pathlib import Path

PROGRAM_NAME = "Musify"
PROGRAM_OWNER_NAME = "George Martin Marino"
PROGRAM_OWNER_USER = "geo-martino"
PROGRAM_OWNER_EMAIL = f"gm.engineer+{PROGRAM_NAME.lower()}@pm.me"
PROGRAM_URL = f"https://github.com/{PROGRAM_OWNER_USER}/{PROGRAM_NAME.lower()}"

MODULE_ROOT: str = Path(__file__).parent.name
PACKAGE_ROOT: Path = Path(__file__).parent.parent
