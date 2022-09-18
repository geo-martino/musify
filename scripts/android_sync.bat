set ANDROID_SERIAL=192.168.178.102:5555

adb connect %ANDROID_SERIAL%
adb shell "mkdir -p /storage/E42C-0EA8/Music/___Playlists"
adb pull "/storage/E42C-0EA8/Music/___Playlists" D:\Music
py "D:\Coding\syncify\main.py" -cfg 
adb shell "rm -rf /storage/E42C-0EA8/Music/___Playlists"
adb push D:\Music\___Playlists "/storage/E42C-0EA8/Music"
rmdir /s /q "D:\Music\___Playlists"