from p3 import *

from musify.libraries.local.library import LocalLibrary

local_library = LocalLibrary(
    library_folders=["<PATH TO YOUR LIBRARY FOLDER>", ...],
    playlist_folder="<PATH TO YOUR PLAYLIST FOLDER>",
    # this wrangler will be needed to interpret matched URIs as valid
    remote_wrangler=api.wrangler,
)
local_library.load()

albums = local_library.albums
