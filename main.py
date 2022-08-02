import argparse
import json
import traceback
from time import perf_counter
from dotenv import load_dotenv
from requests import delete

# load stored environment variables from .env
load_dotenv()

from local.io import LocalIO

from syncify.syncify import Syncify

def get_parser():
    parser = argparse.ArgumentParser(
    description="Sync your local library to Spotify.", prog="syncify",
    usage='%(prog)s [function] [options]')
    parser._positionals.title = 'Functions'
    parser._optionals.title = 'Optional arguments'

    # cli function aliases and expected args in order user should give them
    functions = {
        "main": {"main": []},
        "auth": {"auth": []},
        # individual main steps
        'search': {'search': []},
        'check': {'check': []},
        'update_tags': {'update_tags': []},
        'update_spotify': {'update_spotify': []},
        # reports/maintenance/utilities
        'report': {'report': []},
        'missing_tags': {'missing_tags': ["match"]},
        'backup': {'backup': []},
        'restore': {'restore': ['kind', 'mod']},
        'extract': {'extract': ['kind', 'playlists']},
        "clean_playlists" : {"clean_playlists": []},
        "clean": {"clean_up_env": ['days', 'keep']},
        # endpoints
        "create": {"create_playlist": ['playlist_name', 'public', 'collaborative']},
        "get": {"get_data": ['name']},
        "delete": {"delete_playlist": ['playlist']},
        "clear": {"clear_from_playlist": ['playlist']},
    }
    parser.add_argument('function', nargs='?', default="main", choices=list(functions.keys()),
                        help=f"Syncify function to run.")

    local = parser.add_argument_group("Local library filters and options")
    local.add_argument('-q', '--quickload', required=False, nargs='?', default=False, const=True,
                       help="Skip search/update tags sections of main function. If set, use last run's data for these sections or enter a date to define which run to load from.")
    local.add_argument('-s', '--start', type=str, required=False, nargs='*', dest='prefix_start', metavar='',
                       help='Start processing from the folder with this prefix i.e. <folder>:<END>')
    local.add_argument('-e', '--end', type=str, required=False, nargs='*', dest='prefix_stop', metavar='',
                       help='Stop processing from the folder with this prefix i.e. <START>:<folder>')
    local.add_argument('-l', '--limit', type=str, required=False, nargs='*', dest='prefix_limit', metavar='',
                       help="Only process albums that start with this prefix")
    local.add_argument('-c', '--compilation', action='store_const', const=True,
                       help="Only process albums that are compilations")

    spotify = parser.add_argument_group("Spotify metadata extraction options")
    spotify.add_argument('-ag', '--add-genre', action='store_true',
                         help="Get genres when extracting track metadata from Spotify")
    spotify.add_argument('-af', '--add-features', action='store_true',
                         help="Get audio features when extracting track metadata from Spotify")
    spotify.add_argument('-aa', '--add-analysis', action='store_true',
                         help="Get audio analysis when extracting track metadata from Spotify (long runtime)")
    spotify.add_argument('-ar', '--add-raw', action='store_true',
                         help="Keep raw API data back when extracting track metadata from Spotify")

    playlists = parser.add_argument_group("Playlist processing options")
    playlists.add_argument('-in', '--in-playlists', required=False, nargs='*', metavar='',
                           help=f"Playlist names to include in any playlist processing")
    playlists.add_argument('-ex', '--ex-playlists', required=False, nargs='*', metavar='',
                           help=f"Playlist names to exclude in any playlist processing")
    playlists.add_argument('-f', '--filter', required=False, nargs='?', dest='filter_tags', default=False, const='filter',
                           help="Before updating Spotify playlists, filter out tracks with these tag values. Loads values from json file.")
    playlists.add_argument('-ce', '--clear-extra', action='store_const', dest='clear', default=False, const='extra',
                           help="Clear songs not present locally first when updating current Spotify playlists")
    playlists.add_argument('-ca', '--clear-all', action='store_const', dest='clear', default=False, const='all',
                           help="Clear all songs first when updating current Spotify playlists")

    tags = parser.add_argument_group("Local library tag update options")
    tag_options = list(LocalIO._tag_ids['.flac'].keys()) + ["uri"]
    tags.add_argument('-t', '--tags', required=False, nargs='*', metavar='',
                      choices=tag_options,
                      help=f"List of tags to update from Spotify to local files' metadata. Allowed values: {', '.join(tag_options)}.")
    tags.add_argument('-r', '--replace', action='store_true',
                      help="If set, destructively replace tags when updating local file tags")

    runtime = parser.add_argument_group("Runtime options")
    runtime.add_argument('-o', '--no-output', action='store_true',
                         help="Suppress all json file output, apart from files saved to the parent folder i.e. API token file and URIs.json")
    runtime.add_argument('-v', '--verbose', action='store_true',
                         help="Add additional stats on library to terminal throughout the run")
    runtime.add_argument('-x', '--execute', action='store_false', dest='dry_run',
                         help="Modify users files and playlist. Otherwise, do not affect files and append '_dry' to data folder path.")

    return functions, parser

if __name__ == "__main__":
    functions, parser = get_parser()
    parsed_args = parser.parse_known_args()
    kwargs = vars(parsed_args[0])
    args = parsed_args[1]

    main = Syncify(verbose=kwargs['verbose'], auth=True, dry_run=kwargs["dry_run"])
    main.convert_kwargs(functions, args, kwargs)
    main._logger.debug(f"Args parsed: {args}")
    main._logger.debug(f"Kwargs parsed: \n{json.dumps(kwargs, indent=2)}")

    try:  # run the function requested by the user
        print()
        main._logger.info(f"\33[95mBegin running \33[1;95m{kwargs['function']}\33[0;95m function \33[0m")
        main._logger.info(f"\33[90mLogs output: {main._log_file} \33[0m")
        main._logger.info(f"\33[90mData output: {main.DATA_PATH} \33[0m")

        func = list(functions[kwargs["function"].lower()].keys())[0]
        getattr(main, func)(**kwargs)
    except BaseException:
        main._logger.critical(traceback.format_exc())

    print()
    seconds = perf_counter() - main._start_time
    main._logger.info(
        f"\33[95mSyncified in {int(seconds // 60)} mins {int(seconds % 60)} secs \33[0m")
    main._logger.info(f"\33[90mLogs output: {main._log_file} \33[0m")
    main._logger.info(f"\33[90mData output: {main.DATA_PATH} \33[0m")

# TODO: read and modify m3u and autoxpf files directly
# TODO: track audio recognition when searching using Shazam like service?
# TODO: Automatically add songs added to each Spotify playlist to '2get'?
#       Then somehow update local library playlists after...
#       Maybe add a final step that syncs Spotify back to library if 
#       uris for extra songs in Spotify playlists found in library
