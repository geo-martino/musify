@echo off
@REM set /p "PORT=Enter Android WiFi Port number: "
@REM set ANDROID_SERIAL=192.168.178.102:%PORT%

@REM adb connect %ANDROID_SERIAL%
@REM adb shell "mkdir -p /storage/E42C-0EA8/Music/___Playlists"
@REM adb pull "/storage/E42C-0EA8/Music/___Playlists" D:\Music

"D:\Coding\syncify\.venv\Scripts\python.exe" "D:\Coding\syncify\main.py" -cfg main
"D:\Coding\syncify\.venv\Scripts\python.exe" "D:\Coding\syncify\main.py" -cfg update_tags
echo Metadata sync complete. Update playlists now, then press any key to sync playlists with Spotify
pause
"D:\Coding\syncify\.venv\Scripts\python.exe" "D:\Coding\syncify\main.py" -cfg update_spotify

@REM adb shell "rm -rf /storage/E42C-0EA8/Music/___Playlists"
@REM adb push D:\Music\___Playlists "/storage/E42C-0EA8/Music"
@REM rmdir /s /q "D:\Music\___Playlists"