#!/bin/zsh

setopt +o nomatch
setopt CAse_glob

HOME_EXT=/storage/E42C-0EA8

FILE_TYPES=( jpg jpeg png mp4 mov m4v avi )
unset FIND_TYPES
local -a FIND_TYPES
for ext in "${FILE_TYPES[@]}"; do
    FIND_TYPES+=(-o -iname "*.${ext}")
done
unset 'FIND_TYPES[1]'

# custom paths
PATHS=(
    "$HOME/Pictures/2011-2014/2013 Berlin"
    "$HOME/Pictures/2011-2014/2013 Paris"
    "$HOME/Pictures/2014-2015/2014-2015 Holland"
    "$HOME/Pictures/2014-2015/2015 Brazil"
    "$HOME/Pictures/2014-2015/2015 Moscow"
    "$HOME/Pictures/2015-2016/2016 Eurotrip"
    "$HOME/Pictures/2015-2016/2016 Spain"
    "$HOME/Pictures/2015-2016/2016 _Scotland"
    "$HOME/Pictures/2017/West Side Story"
    "$HOME/Pictures/2018/Jekyll & Hyde"
    "$HOME/Pictures/2019/Sofiya + Kacper Wedding 2019-06-19"
    "$HOME/Pictures/2020/2020 Eurotrip"
    "$HOME/Pictures/2020/2020 Switzerland"
    "$HOME/Pictures/2022/2022 NYC"
    "$HOME/Pictures/2022/2022 Snow"
    "$HOME/Pictures/2022/2022 Toronto"
    "$HOME/Pictures/2023/2023 Prague-Vienna"
    "$HOME/Pictures/2023/2023 Snow"
    "$HOME/Pictures/2023/2023 Toronto"
    "$HOME/Pictures/2023/2023 Portugal"
    "$HOME/Pictures/London Xmas 2015-2016"
    "$HOME/Pictures/Shoots + Misc"
    )

# add all year based folder with 20* prefix and sort paths list
for folder in $(ls -d "$HOME"/Pictures/20*/); do
    PATHS+=("${folder%?}")
done
IFS=$'\n' PATHS=($(sort <<<"${PATHS[*]}"))
unset IFS

### FIND PORT AND CONNECT ###
# if ANDROID_SERIAL not set
if [ -z "$ANDROID_SERIAL" ]; then
  export PHONE_IP=192.168.2.55

  if [ -z "$PHONE_PORT" ]; then
    echo "\033[1;95m-> \033[1;97mScanning for debug port of Android device with IP address $PHONE_IP (sudo required)\033[0m"
    unset PHONE_PORT
    export PHONE_PORT=$(sudo nmap -nsF ${PHONE_IP} -p 30000-49999 | awk -F/ '/tcp open/{print $1}')
  fi

  if (( $(echo "$PHONE_PORT" | wc -l) > 1 )); then
    echo "\n\033[91mERROR: Multiple phone ports found.\033[0m Pick one from:\033[92m"
    echo "$PHONE_PORT" | xargs -n1 echo ' '
    echo -n "\033[93mPort=\033[0m"
    read -r PHONE_PORT
    echo
  fi

  export ANDROID_SERIAL=$PHONE_IP:$PHONE_PORT
  unset PHONE_PORT
  unset PHONE_IP
fi

# if ANDROID_SERIAL device not found in adb devices list
if ! adb devices | grep -q "$ANDROID_SERIAL"; then
  echo "\033[1;95m-> \033[1;97mConnecting to Android with address => $ANDROID_SERIAL\033[0m"
	adb connect "$ANDROID_SERIAL"
fi

for PATH_HOME in "${PATHS[@]}"; do
    echo "\n\033[1;95m-> \033[1;97mProcessing: \033[1;96m$(echo "$PATH_HOME" | sed "s|$HOME/||")\033[0m"

    PATH_EXT=$HOME_EXT$(echo "$PATH_HOME" | sed "s|$HOME||")
    adb shell "mkdir -p \"$PATH_EXT\""
    BASENAME_HOME=("${(@f)$(find "$PATH_HOME" -mindepth 1 -maxdepth 1 -type f $FIND_TYPES | xargs -n1 -i basename "{}" | sort)}")
    BASENAME_EXT=("${(@f)$(adb shell "find \"$PATH_EXT\" -mindepth 1 -maxdepth 1 -type f $FIND_TYPES" | xargs -n1 -i basename "{}" | sort)}")

    echo " > \033[93mHome: ${#BASENAME_HOME[@]} files | Ext: ${#BASENAME_EXT[@]} files\033[0m"

    delete_from_name=$(comm -13 <(printf "%s\n" "${BASENAME_HOME[@]}") <(printf "%s\n" "${BASENAME_EXT[@]}") | head -n 1)
    if [ -n "$delete_from_name" ]; then
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

    BASENAME_EXT=("${(@f)$(adb shell "find \"$PATH_EXT\" -mindepth 1 -maxdepth 1 $FIND_TYPES -type f" | xargs -n1 -i basename "{}" | sort)}") 2>/dev/null
    copy_from_name=$(comm -13 <(printf "%s\n" "${BASENAME_EXT[@]}") <(printf "%s\n" "${BASENAME_HOME[@]}") | head -n 1)
    if [ -n "$copy_from_name" ]; then
        echo " · \033[92mCopying files from $copy_from_name\033[0m"
        copy_from_path=$PATH_HOME/$copy_from_name
        copy=false

        for name in "${BASENAME_HOME[@]}"; do
            filepath="$PATH_HOME/$name"
            if [ "$filepath" = "$copy_from_path" ]; then copy=true; fi
            if [ "$copy" = true ]; then adb push "$filepath" "$PATH_EXT"/ 1>/dev/null; fi
            echo =
        done | pv -N 'Copying files to device' -l -s ${#BASENAME_HOME[@]} > /dev/null
    fi
done

# TODO: checksum on files which have matching filenames in src and trg
#  replace trg with src if checksums don't match