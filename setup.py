from cx_Freeze import setup, Executable

# Dependencies are automatically detected, but it might need fine-tuning.
options = {"build_exe": {"packages": [],
                         "include_files": ["README.md", "LICENSE"],
                         "optimize": 1},
           "build": {"build_exe": "build/syncify_v0.3"},
           "install_exe": {"force": True},
           }

target = Executable(
    script="main.py",
    target_name="syncify",
    base="Console"
)

setup(
    name="Syncify",
    version="0.3",
    description="Synchronise your music library to Spotify",
    author="George M. Marino",
    options=options,
    executables=[target]
)
