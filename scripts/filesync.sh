#!/bin/zsh

setopt +o nomatch
setopt CAse_glob

HOME_EXT=/storage/E42C-0EA8

FILE_TYPES=( jpg jpeg png mp4 mov m4v avi )
local -a FIND_TYPES
for ext in "${FILE_TYPES[@]}"; do
    FIND_TYPES+=(-o -iname "*.${ext}")
done
unset 'FIND_TYPES[1]'

PATHS=(
    "$HOME/Pictures/2001-2011"
    "$HOME/Pictures/2011-2014"
    "$HOME/Pictures/2011-2014/2013 Berlin"
    "$HOME/Pictures/2011-2014/2013 Paris"
    "$HOME/Pictures/2014-2015"
    "$HOME/Pictures/2014-2015/2014-2015 Holland"
    "$HOME/Pictures/2014-2015/2015 Brazil"
    "$HOME/Pictures/2014-2015/2015 Moscow"
    "$HOME/Pictures/2015-2016"
    "$HOME/Pictures/2015-2016/2016 Eurotrip"
    "$HOME/Pictures/2015-2016/2016 Spain"
    "$HOME/Pictures/2015-2016/2016 _Scotland"
    "$HOME/Pictures/2017"
    "$HOME/Pictures/2017/West Side Story"
    "$HOME/Pictures/2018"
    "$HOME/Pictures/2018/Jekyll & Hyde"
    "$HOME/Pictures/2019"
    "$HOME/Pictures/2019/Sofiya + Kacper Wedding 2019-06-19"
    "$HOME/Pictures/2020"
    "$HOME/Pictures/2020/2020 Eurotrip"
    "$HOME/Pictures/2020/2020 Switzerland"
    "$HOME/Pictures/2021"
    "$HOME/Pictures/2022"
    "$HOME/Pictures/2022/2022 NYC"
    "$HOME/Pictures/2022/2022 Snow"
    "$HOME/Pictures/2022/2022 Toronto"
    "$HOME/Pictures/London Xmas 2015-2016"
    "$HOME/Pictures/Shoots + Misc"
    "$HOME/Pictures/Wallpapers"
    )

### FIND PORT AND CONNECT ###
# if ANDROID_SERIAL not set or ANDROID_SERIAL is set and device not found in adb devices list
if [ -z "$ANDROID_SERIAL" ] || [ -z "$(adb devices | grep "$ANDROID_SERIAL")" ]; then
    export PHONE_IP=192.168.178.102
    echo "\033[1;95m-> \033[1;97mScanning for debug port of Android device with IP address $PHONE_IP\033[0m"
    export PHONE_PORT=$(sudo nmap -nsF ${PHONE_IP} -p 30000-49999 | awk -F/ '/tcp open/{print $1}')
    export ANDROID_SERIAL=$PHONE_IP:$PHONE_PORT
    adb connect $ANDROID_SERIAL
fi

for PATH_HOME in "${PATHS[@]}"; do
    echo "\n\033[1;95m-> \033[1;97mProcessing: \033[1;96m$(echo $PATH_HOME | sed "s|$HOME/||")\033[0m"

    PATH_EXT=$HOME_EXT$(echo $PATH_HOME | sed "s|$HOME||")
    BASENAME_HOME=("${(@f)$(find "$PATH_HOME" -mindepth 1 -maxdepth 1 $FIND_TYPES -type f | xargs -n1 -i basename "{}" | sort)}")
    BASENAME_EXT=("${(@f)$(adb shell "find \"$PATH_EXT\" -mindepth 1 -maxdepth 1 $FIND_TYPES -type f" | xargs -n1 -i basename "{}" | sort)}")

    echo " > \033[93mHome: ${#BASENAME_HOME[@]} files | Ext: ${#BASENAME_EXT[@]} files\033[0m"

    delete_from_name=$(comm -13 <(printf "%s\n" "${BASENAME_HOME[@]}") <(printf "%s\n" "${BASENAME_EXT[@]}") | head -n 1)
    if [ ! -z "$delete_from_name" ]; then
        echo " · \033[91mDeleting files from $delete_from_name\033[0m"
        delete_from_path=$PATH_EXT/$delete_from_name
        delete=false

        for name in "${BASENAME_EXT[@]}"; do
            filepath="$PATH_EXT/$name"
            if [ "$filepath" = "$delete_from_path" ]; then delete=true; fi
            if [ "$delete" = true ]; then adb shell "rm -f '$filepath'"; fi
            echo =
        done | pv -N 'Deleting files from device' -l -s ${#BASENAME_EXT[@]} > /dev/null
    fi

    BASENAME_EXT=("${(@f)$(adb shell "find \"$PATH_EXT\" -mindepth 1 -maxdepth 1 $FIND_TYPES -type f" | xargs -n1 -i basename "{}" | sort)}")
    copy_from_name=$(comm -13 <(printf "%s\n" "${BASENAME_EXT[@]}") <(printf "%s\n" "${BASENAME_HOME[@]}") | head -n 1)
    if [ ! -z "$copy_from_name" ]; then
        echo " · \033[92mCopying files from $copy_from_name\033[0m"
        copy_from_path=$PATH_HOME/$copy_from_name
        copy=false

        for name in "${BASENAME_HOME[@]}"; do
            filepath="$PATH_HOME/$name"
            if [ "$filepath" = "$copy_from_path" ]; then copy=true; fi
            if [ "$copy" = true ]; then adb push $filepath $PATH_EXT/ 1>/dev/null; fi
            echo =
        done | pv -N 'Copying files to device' -l -s ${#BASENAME_HOME[@]} > /dev/null
    fi
done