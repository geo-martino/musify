#!/bin/zsh

setopt +o nomatch
setopt CAse_glob

PHONE_INTERNAL=/storage/self/primary
PHONE_SD=/storage/E42C-0EA8
LAST_EXPORT='2023-06-28 18:22:13'
THIS_EXPORT=$(date '+%Y-%m-%d %H:%M:%S')

### CREATE DIRECTORIES ###
export SORT_FOLDER=$HOME/Pictures/___2sort
export SORT_OTHER=$SORT_FOLDER/ProcessMe
export SORT_CAMERA=$SORT_FOLDER/Camera
export SORT_WHATSAPP=$SORT_FOLDER/WhatsApp
export SORT_IPHONE=$SORT_FOLDER/iPhone
export SORT_IPHONE_LIVE=$SORT_IPHONE/Live
export SORT_LIVE=$SORT_FOLDER/Live
export SORT_OTHER_LIVE=$SORT_OTHER/Live
mkdir -p \
  "$SORT_IPHONE" \
  "$SORT_IPHONE_LIVE" \
  "$SORT_CAMERA" \
  "$SORT_WHATSAPP" \
  "$SORT_OTHER" \
  "$SORT_OTHER_LIVE"

### FIND PORT AND CONNECT ###
# if ANDROID_SERIAL not set
if [ -z "$ANDROID_SERIAL" ]; then
  export PHONE_IP=192.168.2.55

  if [ -z "$PHONE_PORT" ]; then
    echo "\n\033[1;95m-> \033[1;97mScanning for debug port of Android device with IP address $PHONE_IP (sudo required)\033[0m"
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
  echo "\n\033[1;95m-> \033[1;97mConnecting to Android with address => $ANDROID_SERIAL\033[0m"
	adb connect "$ANDROID_SERIAL"
fi

if adb devices | grep "$ANDROID_SERIAL" | grep -v -q "offline"; then
	echo "\n\033[1;95m-> \033[1;97mExtracting files created since $LAST_EXPORT\033[0m"
	# ### COPY ###
	adb shell "find '$PHONE_INTERNAL/DCIM/Camera' \
		-mindepth 1 -maxdepth 1 -type f -newerct '$LAST_EXPORT' 2>/dev/null" | \
		xargs -i sh -c 'adb pull "{}" $SORT_CAMERA && adb shell "rm \"{}\""'
	adb shell "find '$PHONE_SD/DCIM/Camera' \
		-mindepth 1 -maxdepth 1 -type f -newerct '$LAST_EXPORT' 2>/dev/null" | \
		xargs -i sh -c 'adb pull "{}" $SORT_CAMERA && adb shell "rm \"{}\""'
	adb shell "find '$PHONE_INTERNAL/DCIM/Screenshots' \
		-mindepth 1 -maxdepth 1 -type f -newerct '$LAST_EXPORT' 2>/dev/null" | \
		xargs -i sh -c 'adb pull "{}" $SORT_OTHER && adb shell "rm \"{}\""'
	adb shell "find '$PHONE_SD/DCIM/Screenshots' \
		-mindepth 1 -maxdepth 1 -type f -newerct '$LAST_EXPORT' 2>/dev/null" | \
		xargs -i sh -c 'adb pull "{}" $SORT_OTHER && adb shell "rm \"{}\""'
	adb shell "find '$PHONE_INTERNAL/DCIM/Facebook' \
		-mindepth 1 -maxdepth 1 -type f -newerct '$LAST_EXPORT' 2>/dev/null" | \
		xargs -i sh -c 'adb pull "{}" $SORT_OTHER && adb shell "rm \"{}\""'
	adb shell "find '$PHONE_INTERNAL/Movies/Instagram' \
		-mindepth 1 -maxdepth 1 -type f -newerct '$LAST_EXPORT' 2>/dev/null" | \
		xargs -i sh -c 'adb pull "{}" $SORT_OTHER && adb shell "rm \"{}\""'
	adb shell "find '$PHONE_INTERNAL/Movies/Messenger' \
		-mindepth 1 -maxdepth 1 -type f -newerct '$LAST_EXPORT' 2>/dev/null" | \
		xargs -i sh -c 'adb pull "{}" $SORT_OTHER && adb shell "rm \"{}\""'
	adb shell "find '$PHONE_INTERNAL/Pictures/Instagram' \
		-mindepth 1 -maxdepth 1 -type f -newerct '$LAST_EXPORT' 2>/dev/null" | \
		xargs -i sh -c 'adb pull "{}" $SORT_OTHER && adb shell "rm \"{}\""'
	adb shell "find '$PHONE_INTERNAL/Pictures/Messenger' \
		-mindepth 1 -maxdepth 1 -type f -newerct '$LAST_EXPORT' 2>/dev/null" | \
		xargs -i sh -c 'adb pull "{}" $SORT_OTHER && adb shell "rm \"{}\""'
	adb shell "find '$PHONE_INTERNAL/Pictures/Slack' \
		-mindepth 1 -maxdepth 1 -type f -newerct '$LAST_EXPORT' 2>/dev/null" | \
		xargs -i sh -c 'adb pull "{}" $SORT_OTHER && adb shell "rm \"{}\""'
	adb shell "find '$PHONE_INTERNAL/Pictures/Whatsapp' \
		-mindepth 1 -maxdepth 1 -type f -newerct '$LAST_EXPORT' 2>/dev/null" | \
		xargs -i sh -c 'adb pull "{}" $SORT_OTHER && adb shell "rm \"{}\""'
	adb shell "find '$PHONE_INTERNAL/Android/media/com.whatsapp/WhatsApp/Media/WhatsApp Images' \
		-mindepth 1 -maxdepth 1 -type f -iname '*.jpg' -o -iname '*.jpeg' -newerct '$LAST_EXPORT'" | \
		xargs -i sh -c 'adb pull "{}" $SORT_WHATSAPP && adb shell "rm \"{}\""'
	adb shell "find '$PHONE_INTERNAL/Android/media/com.whatsapp/WhatsApp/Media/WhatsApp Video' \
		-mindepth 1 -maxdepth 1 -type f -iname '*.mp4' -o -iname '*.mpeg4' -newerct '$LAST_EXPORT'" | \
		xargs -i sh -c 'adb pull "{}" $SORT_WHATSAPP && adb shell "rm \"{}\""'
else
	echo "\n\033[1;95m-> \033[93mSkipping file extraction: phone not found\033[0m"
fi

### PROCESS ###
export TIMESTAMP_PATTERN_FINAL='([0-9]{4}-[0-9]{2}-[0-9]{2}_[0-9]{2}\.[0-9]{2}\.[0-9]{2})'
export TIMESTAMP_PATTERN_PHONE='([0-9]{4})([0-9]{2})([0-9]{2})_([0-9]{2})([0-9]{2})([0-9]{2})'
export TIMESTAMP_PATTERN_INDEX="${TIMESTAMP_PATTERN_FINAL}_([^.]*)"

# remove empty folders
rmdir --ignore-fail-on-non-empty \
	"$SORT_CAMERA" \
	"$SORT_IPHONE_LIVE" \
	"$SORT_IPHONE" \
	"$SORT_LIVE" \
  "$SORT_OTHER_LIVE" \
	"$SORT_OTHER" \
	"$SORT_WHATSAPP" \
	2>/dev/null

if [ -d "$SORT_CAMERA" ]
then
	echo "\n\033[1;95m-> \033[1;97mProcessing $(ls -1 "$SORT_CAMERA" | wc -l) files in Camera\033[0m"
	# Rename from %Y%m%d_%H%M%S.(EXT) to %Y-%m-%d_%H.%M.%S.(EXT)
	find "$SORT_CAMERA" -mindepth 1 -maxdepth 1 \
		-type f -regextype posix-egrep -regex '.*/[0-9]{8}_[0-9]{6}.*' | \
		sed -r "s|(.*)/$TIMESTAMP_PATTERN_PHONE.*\.([a-zA-Z0-9]{2,})|& \1/\2-\3-\4_\5.\6.\7\.\8|g" | \
		xargs -n 2 mv
	
	# Move timestamped files to main sort folder safely
	find "$SORT_CAMERA" -mindepth 1 -exec mv -n {} "$SORT_FOLDER" \; 2>/dev/null
fi


if [ -d "$SORT_IPHONE" ]
then
	echo "\n\033[1;95m-> \033[1;97mProcessing $(ls -1 "$SORT_IPHONE" | wc -l) files in iPhone\033[0m"
	rm -f "$SORT_IPHONE"/*.AAE
	mkdir -p "$SORT_IPHONE_LIVE" "$SORT_OTHER" "$SORT_OTHER_LIVE"

	# move live photos
	echo "\033[1;95m · \033[1;97mMoving $(find "$SORT_IPHONE" -mindepth 1 -maxdepth 1 -type f -iname '*.MOV' | wc -l) live videos\033[0m"
	ls "$SORT_IPHONE" | \
		cut -f1 -d. | \
		uniq -d | \
		xargs -i echo "$SORT_IPHONE"/{}.MOV | \
		xargs -i mv {} "$SORT_IPHONE_LIVE"
	
	# rename live photos based on original photo's metadata
	rmdir --ignore-fail-on-non-empty "$SORT_IPHONE_LIVE"
	if [ -d "$SORT_IPHONE_LIVE" ]
	then
		echo "\033[1;95m · \033[1;97mProcessing live photos/videos\033[0m"
		exiftool -csv -ext jpg -FileName -DateTimeOriginal \
			-d %Y-%m-%d_%H.%M.%S "$SORT_IPHONE" > "$SORT_IPHONE"/rename.csv
		cut -d , -f 2-3 "$SORT_IPHONE"/rename.csv | \
			grep -v ",$" | \
			sed 's|,| |g' | \
			sed '/FileName/d' | \
			sed -r "s|(\S+)\.\w+ (\S+)|$SORT_IPHONE_LIVE/\1.MOV $SORT_IPHONE_LIVE/\2\.MOV|gI" | \
			xargs -n2 sh -c 'mv -n $0 $1' 2>/dev/null
		rm -f "$SORT_IPHONE"/rename.csv
	fi

	# rename image files based on metadata
	echo "\033[1;95m · \033[1;97mAttempting to rename images based on metadata\033[0m"
	exiftool -ext jpg '-FileName<${DateTimeOriginal}_${filename;$_=substr($_,-8,4)}.%e' \
		-d "%Y-%m-%d_%H.%M.%S" "$SORT_IPHONE" 2>/dev/null
	exiftool -ext jpeg '-FileName<${DateTimeOriginal}_${filename;$_=substr($_,-9,4)}.%e' \
		-d "%Y-%m-%d_%H.%M.%S" "$SORT_IPHONE" 2>/dev/null
	exiftool -ext png '-FileName<${DateTimeOriginal}_${filename;$_=substr($_,-8,4)}.%e' \
		-d "%Y-%m-%d_%H.%M.%S" "$SORT_IPHONE" 2>/dev/null
	exiftool -ext heic '-FileName<${DateTimeOriginal}_${filename;$_=substr($_,-9,4)}.%e' \
		-d "%Y-%m-%d_%H.%M.%S" "$SORT_IPHONE" 2>/dev/null

	# convert heic files to jpg and remove original
	echo "\033[1;95m · \033[1;97mConverting $(find "$SORT_IPHONE" -mindepth 1 -maxdepth 1 -type f -iname '*.HEIC' | wc -l) HEIC images to JPG\033[0m"
	find "$SORT_IPHONE" -mindepth 1 -maxdepth 1 \
		-type f -iname '*.HEIC' | \
		sed -r "s|(.*)\.(\S+)|\1.\2 \1.jpg|g" | \
		xargs -n2 bash -c 'heif-convert -q 100 $0 $1 && rm -f $0' 1>/dev/null

	if [ -d "$SORT_IPHONE_LIVE" ]
	then
    # rename live video files based on metadata
    echo "\033[1;95m · \033[1;97mAttempting to rename live videos based on metadata\033[0m"
    find "$SORT_IPHONE_LIVE" -mindepth 1 -maxdepth 1 \
      -type f -iname '*.MOV' | \
      xargs -i sh -c 'echo {} $(mediainfo \
      --Inform="General;%com.apple.quicktime.creationdate%" {} | \
      sed -r "s|[+-][0-9]{2}.?[0-9]{2}$||g" | \
      xargs -I {} date -d {} +%Y-%m-%d_%H.%M.%S) | \
      sed -r "s|(\S+) (\S+)|\1 $SORT_IPHONE_LIVE/\2.MOV|g"' | \
      xargs -n2 mv -n
	fi

	# rename video files based on metadata
	echo "\033[1;95m · \033[1;97mAttempting to rename videos based on metadata\033[0m"
	find "$SORT_IPHONE" -mindepth 1 -maxdepth 1 \
		-type f -iname '*.MOV' | \
		xargs -i sh -c 'echo {} $(mediainfo \
		--Inform="General;%com.apple.quicktime.creationdate%" {} | \
		sed -r "s|[+-][0-9]{2}.?[0-9]{2}$||g" | \
		xargs -I {} date -d {} +%Y-%m-%d_%H.%M.%S) | \
		sed -n -r "s|(\S+) (\S+)|\1 $SORT_IPHONE/\2.MOV|p"' | \
		xargs -n2 mv -n

	echo "\033[1;95m · \033[1;97mAttempting to remove indexes from files if present\033[0m"
	# Do not rename files if file with the same timestamp already exists
	find "$SORT_IPHONE" -mindepth 1 -maxdepth 1 \
		-type f -regextype posix-egrep -regex ".*/$TIMESTAMP_PATTERN_INDEX.*" | \
		sed -r "s|(.*)/$TIMESTAMP_PATTERN_INDEX(.*)|\1/\2_\3\4 \1/\2\4|g" | \
		xargs -n2 mv -n

	# Move all that do not match expected timestamp filename pattern
	echo "\033[1;95m · \033[1;97mMoving files with invalid filenames\033[0m"
	find "$SORT_IPHONE" -mindepth 1 -maxdepth 1 \
		-type f -regextype posix-egrep -not -regex ".*/$TIMESTAMP_PATTERN_FINAL\\..*" | \
		xargs -i mv -i {} "$SORT_OTHER"
	find "$SORT_IPHONE_LIVE" -mindepth 1 -maxdepth 1 \
		-type f -regextype posix-egrep -not -regex ".*/$TIMESTAMP_PATTERN_FINAL\\..*" | \
		xargs -i mv -i {} "$SORT_OTHER_LIVE"
	
	# Move all remaining files to main sort folder safely
	echo "\033[1;95m · \033[1;97mMoving files with valid filenames\033[0m"
	find "$SORT_IPHONE" -mindepth 1 -maxdepth 1 -exec mv -n {} "$SORT_FOLDER" \; 2>/dev/null
fi

### CLEAN UP ###
# Move files left behind to folder for further processing and cleanup
[ -d "$SORT_CAMERA" ] && find "$SORT_CAMERA" -mindepth 1 \
	-exec mv -n {} "$SORT_OTHER" \; 2>/dev/null
[ -d "$SORT_IPHONE" ] && find "$SORT_IPHONE" -mindepth 1 \
	-exec mv -n {} "$SORT_OTHER" \; 2>/dev/null

rmdir --ignore-fail-on-non-empty \
	"$SORT_CAMERA" \
	"$SORT_IPHONE_LIVE" \
	"$SORT_IPHONE" \
	"$SORT_LIVE" \
  "$SORT_OTHER_LIVE" \
	"$SORT_OTHER" \
	"$SORT_WHATSAPP" \
	"$SORT_FOLDER" \
	2>/dev/null

if [ -d "$SORT_FOLDER" ]
then
	echo "\n · \033[92m$(find "$SORT_FOLDER" -maxdepth 1 -type f | wc -l) files processed with timestamps\033[0m"
	if [ -d "$SORT_LIVE" ]
	then
		# remove any live videos no longer present in main folder
		# useful on a 2nd run after deleting photos in the main sort folder
		comm -13 \
			<(printf "%s\n" $(find "$SORT_FOLDER" -mindepth 1 -maxdepth 1 -type f | xargs -n1 basename | sed -r "s|$TIMESTAMP_PATTERN_FINAL.*|\1.MOV|g")) \
			<(printf "%s\n" $(find "$SORT_LIVE" -mindepth 1 -maxdepth 1 -type f | xargs -n1 basename)) | \
			xargs -n1 -i rm "$SORT_LIVE"/{}
		echo " · \033[92m$(find "$SORT_LIVE" -maxdepth 1 -type f | wc -l) live videos processed\033[0m"
	fi
	if [ -d "$SORT_WHATSAPP" ]
	then
		echo " · \033[91m$(find "$SORT_WHATSAPP" -maxdepth 1 -type f | wc -l) WhatsApp files need manual processing\033[0m"
	fi
	if [ -d "$SORT_OTHER" ]
	then
		echo " · \033[91m$(find "$SORT_OTHER" -maxdepth 1 -type f | wc -l) other files need manual processing\033[0m"
	fi
else
	echo " · \033[93mNo files processed\033[0m" 
fi

#echo "\n\033[1;95m-> \033[1;97mUpdating last export time to $THIS_EXPORT\033[0m"
#sed -r -i "s|^LAST_EXPORT=.*|LAST_EXPORT='$THIS_EXPORT'|g" "${0:a}"

echo

