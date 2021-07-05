from cx_Freeze import setup, Executable

# Dependencies are automatically detected, but it might need fine tuning.
options = {"build_exe": {"packages": [],
                         "include_files": ['README.md', 'LICENSE'],
                         "optimize": 1},
           "build": {"build_exe": "build/m3u2spotify_v1.0"},
           "install_exe": {"force": True},
           }

target = Executable(
    script="main.py",
    target_name='m3u2spotify',
    base='Console'
)

setup(
    name="m3u2spotify",
    version="1.0",
    description="Creates Spotify playlists from m3u files",
    author="George M. Marino",
    options=options,
    executables=[target]
)
