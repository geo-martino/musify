import os

from m3u2spotify.data import Data
from m3u2spotify.spotify import Spotify

if __name__ == "__main__":
    env_name = None
    for file in os.listdir():
        if 'secret' in file or '.env' in file:
            env_name = file
            break

    if env_name is None:
        exit('Secrets file not found.')

    data = Data()
    spotify = Spotify(env_name)

    m3u_playlists = data.get_m3u_metadata(os.environ['PLAYLIST_FOLDER'])
    data.save_json(m3u_playlists, 'm3u_metadata')
    m3u_playlists = data.import_uri(m3u_playlists)
    print('\n', '-' * 88, '\n', sep='')

    headers = spotify.auth_user()
    spotify_playlists = spotify.get_spotify_metadata(m3u_playlists, headers)
    print('\n', '-' * 88, '\n', sep='')

    updated_uris = spotify.update_uris(m3u_playlists, spotify_playlists)
    data.save_json(updated_uris, 'updated_uris')
    data.export_uri(updated_uris)
    print('\n', '-' * 88, '\n', sep='')

    add, missing = spotify.search_all(m3u_playlists, headers)
    print('\n', '-' * 88, '\n', sep='')

    spotify.update_playlist(add, spotify_playlists, headers)
    print('\n', '-' * 88, '\n', sep='')

    data.save_json(add, 'added')
    data.save_json(missing, 'missing_uris')
    data.export_uri(add)
    print('\n', '-' * 88, '\n', sep='')
