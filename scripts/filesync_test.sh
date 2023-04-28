#!/bin/bash

# adb shell "find /storage/E42C-0EA8/Music/ -mindepth 1 \
#     -iname '*.flac' -print0 -o -iname '*.mp3' -print0 -o \
#     -iname '*.m4a' -print0 -o -iname '*.wma' -print0 | \
#     xargs -n1 -0 stat --format='%Y %n' | \
#     sed 's|/storage/E42C-0EA8/Music/||'" | \
#     sed -r -e "s|/mnt/d/Music/||" -e "s|.mp3$||" -e "s|.flac$||" -e "s|.m4a$||" -e "s|.wma$||"

# find /mnt/d/Music -mindepth 1 \
#     -iname '*.flac' -o -iname '*.mp3' -o \
#     -iname '*.m4a' -o -iname '.*wma' | \
#     sed -r "s|/mnt/d/Music/|/storage/E42C-0EA8/Music/|" -e "s|.flac$|.mp3|" | \
#     xargs -n1 -d '\n' echo

LAST_EXPORT='2022-09-10 01:13:46'
THIS_EXPORT=$(date '+%Y-%m-%d %H:%M:%S')

compare_mtime () {
    ext=$(adb shell "stat --format=\"%Y\" \"$(echo "$@" | sed -r -e "s|/mnt/d/Music/|/storage/E42C-0EA8/Music/|" -e "s|.flac|.mp3|")\"")
    local=$(stat --format="%Y" "$@")

    if [ $ext -lt $local ];
    then
        echo "YES $ext $local $1"
    else
        echo "NO $ext $local $1"
    fi
} 


export -f compare_mtime

find "/mnt/d/Music" \
    -iname '*.flac' -newermt "$LAST_EXPORT" -print0 -o \
    -iname '*.mp3' -newermt "$LAST_EXPORT" -print0 -o \
    -iname '*.m4a' -newermt "$LAST_EXPORT" -print0 -o \
    -iname '*.wma' -newermt "$LAST_EXPORT" -print0 | \
    xargs -n1 -0 stat --format='%y %n'