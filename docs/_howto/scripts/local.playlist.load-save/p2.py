from p1 import *

from musify.libraries.local.playlist import XAutoPF

playlist = M3U("<PATH TO AN M3U PLAYLIST>")
playlist = XAutoPF("<PATH TO AN XAUTOPF PLAYLIST>")

# pretty print information about this playlist
print(playlist)
