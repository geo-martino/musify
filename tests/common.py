import os
from os.path import join, dirname, exists

path_root = dirname(dirname(__file__))

path_cache = join(path_root, ".test_cache")
if not exists(path_cache):
    os.makedirs(path_cache)

path_resources = join(dirname(__file__), "__resources")

path_file_flac = join(path_resources, "noise_flac.flac")
path_file_mp3 = join(path_resources, "noise_mp3.mp3")
path_file_m4a = join(path_resources, "noise_m4a.m4a")
path_file_wma = join(path_resources, "noise_wma.wma")
path_file_txt = join(path_resources, "noise.txt")
path_file_img = join(path_resources, "track_image.jpg")