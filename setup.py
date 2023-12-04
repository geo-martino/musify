from cx_Freeze import setup, Executable

from syncify import PROGRAM_NAME

# Dependencies are automatically detected, but it might need fine-tuning.
options = {"build_exe": {"packages": [],
                         "include_files": ["README.md", "LICENSE"],
                         "optimize": 1},
           "build": {"build_exe": f"build/{PROGRAM_NAME.casefold()}_v0.3"},
           "install_exe": {"force": True},
           }

target = Executable(
    script="main.py",
    target_name=PROGRAM_NAME.casefold(),
    base="Console"
)

setup(
    name=PROGRAM_NAME,
    version="0.3",
    description="Synchronise your music library to local or remote libraries",
    author="George M. Marino",
    options=options,
    executables=[target]
)
