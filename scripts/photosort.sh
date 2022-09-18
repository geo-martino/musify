#!/bin/bash

setopt +o nomatch

SORT_FOLDER=$HOME/Pictures/___2sort
PHONE_INTERNAL=/storage/self/primary
PHONE_SD=/storage/E42C-0EA8
LAST_EXPORT='2022-08-29 01:13:46'
THIS_EXPORT=$(date '+%Y-%m-%d %H:%M:%S')

### CONNECT AND CREATE DIRECTORIES ###
adb connect $ANDROID_SERIAL
mkdir -p $SORT_FOLDER/iPhone/ \
	$SORT_FOLDER/iPhone/Live \
	$SORT_FOLDER/Camera/ \
	$SORT_FOLDER/ProcessMe/ \
	$SORT_FOLDER/WhatsApp/ \

### COPY ###
adb shell "find '$PHONE_INTERNAL/DCIM/Camera' \
	-mindepth 1 -maxdepth 1 -type f -newerct '$LAST_EXPORT' 2>/dev/null" | \
	xargs -i sh -c 'adb pull {} $SORT_FOLDER/Camera/ \
	&& adb shell "rm \"{}\""'
adb shell "find '$PHONE_SD/DCIM/Camera' \
	-mindepth 1 -maxdepth 1 -type f -newerct '$LAST_EXPORT' 2>/dev/null" | \
	xargs -i sh -c 'adb pull {} $SORT_FOLDER/Camera/ \
	&& adb shell "rm \"{}\""'
adb shell "find '$PHONE_INTERNAL/DCIM/Screenshots' \
	-mindepth 1 -maxdepth 1 -type f -newerct '$LAST_EXPORT' 2>/dev/null" | \
	xargs -i sh -c 'adb pull {} $SORT_FOLDER/ProcessMe/ \
	&& adb shell "rm \"{}\""'
adb shell "find '$PHONE_SD/DCIM/Screenshots' \
	-mindepth 1 -maxdepth 1 -type f -newerct '$LAST_EXPORT' 2>/dev/null" | \
	xargs -i sh -c 'adb pull {} $SORT_FOLDER/ProcessMe/ \
	&& adb shell "rm \"{}\""'
adb shell "find '$PHONE_INTERNAL/DCIM/Facebook' \
	-mindepth 1 -maxdepth 1 -type f -newerct '$LAST_EXPORT' 2>/dev/null" | \
	xargs -i sh -c 'adb pull {} $SORT_FOLDER/ProcessMe/ \
	&& adb shell "rm \"{}\""'
adb shell "find '$PHONE_INTERNAL/Movies/Instagram' \
	-mindepth 1 -maxdepth 1 -type f -newerct '$LAST_EXPORT' 2>/dev/null" | \
	xargs -i sh -c 'adb pull {} $SORT_FOLDER/ProcessMe/ \
	&& adb shell "rm \"{}\""'
adb shell "find '$PHONE_INTERNAL/Movies/Messenger' \
	-mindepth 1 -maxdepth 1 -type f -newerct '$LAST_EXPORT' 2>/dev/null" | \
	xargs -i sh -c 'adb pull {} $SORT_FOLDER/ProcessMe/ \
	&& adb shell "rm \"{}\""'
adb shell "find '$PHONE_INTERNAL/Pictures/Instagram' \
	-mindepth 1 -maxdepth 1 -type f -newerct '$LAST_EXPORT' 2>/dev/null" | \
	xargs -i sh -c 'adb pull {} $SORT_FOLDER/ProcessMe/ \
	&& adb shell "rm \"{}\""'
adb shell "find '$PHONE_INTERNAL/Pictures/Messenger' \
	-mindepth 1 -maxdepth 1 -type f -newerct '$LAST_EXPORT' 2>/dev/null" | \
	xargs -i sh -c 'adb pull {} $SORT_FOLDER/ProcessMe/ \
	&& adb shell "rm \"{}\""'
adb shell "find '$PHONE_INTERNAL/Pictures/Slack' \
	-mindepth 1 -maxdepth 1 -type f -newerct '$LAST_EXPORT' 2>/dev/null" | \
	xargs -i sh -c 'adb pull {} $SORT_FOLDER/ProcessMe/ \
	&& adb shell "rm \"{}\""'
adb shell "find '$PHONE_INTERNAL/Pictures/Whatsapp' \
	-mindepth 1 -maxdepth 1 -type f -newerct '$LAST_EXPORT' 2>/dev/null" | \
	xargs -i sh -c 'adb pull {} $SORT_FOLDER/ProcessMe/ \
	&& adb shell "rm \"{}\""'
adb shell "find '$PHONE_INTERNAL/Android/media/com.whatsapp/WhatsApp/Media/WhatsApp Images' \
	-mindepth 1 -maxdepth 1 -type f -iname '*.jpg' -o -iname '*.jpeg' -newerct '$LAST_EXPORT'" | \
	xargs -i sh -c 'adb pull "{}" $SORT_FOLDER/WhatsApp \
	&& adb shell "rm \"{}\""'
adb shell "find '$PHONE_INTERNAL/Android/media/com.whatsapp/WhatsApp/Media/WhatsApp Video' \
	-mindepth 1 -maxdepth 1 -type f -iname '*.mp4' -o -iname '*.mpeg4' -newerct '$LAST_EXPORT'" | \
	xargs -i sh -c 'adb pull "{}" $SORT_FOLDER/WhatsApp \
	&& adb shell "rm \"{}\""'

### PROCESS ###
TIMESTAMP_PATTERN_FINAL='[0-9]{4}-[0-9]{2}-[0-9]{2}_[0-9]{2}\.[0-9]{2}\.[0-9]{2}_[0-9]{4}'
TIMESTAMP_PATTERN_PHONE='([0-9]{4})([0-9]{2})([0-9]{2})_([0-9]{2})([0-9]{2})([0-9]{2})'

# remove empty folders
rmdir --ignore-fail-on-non-empty \
	$SORT_FOLDER/Camera \
	$SORT_FOLDER/iPhone/Live \
	$SORT_FOLDER/iPhone \
	$SORT_FOLDER/Live \
	$SORT_FOLDER/ProcessMe \
	$SORT_FOLDER/WhatsApp \
	2>/dev/null

if [ -d $SORT_FOLDER/Camera ] 
then
	# Rename from %Y%m%d_%H%M%S.(EXT) to %Y-%m-%d_%H.%M.%S.(EXT)
	find $SORT_FOLDER/Camera -mindepth 1 -maxdepth 1 \
		-type f -regextype posix-egrep -regex '.*/[0-9]{8}_[0-9]{6}.*' | \
		sed -r "s|(.*)/$TIMESTAMP_PATTERN_PHONE.*\.([a-zA-Z0-9]{2,})|& \1/\2-\3-\4_\5.\6.\7\.\8|g" | \
		xargs -n 2 mv
	
	# Move timestamped files to main sort folder safely
	find $SORT_FOLDER/Camera -mindepth 1 -exec mv -n {} $SORT_FOLDER \; 2>/dev/null
fi


if [ -d $SORT_FOLDER/iPhone ] 
then
	rm -f $SORT_FOLDER/iPhone/*.AAE
	LIVE_FOLDER=$SORT_FOLDER/iPhone/Live
	mkdir -p $LIVE_FOLDER

	# Move live photos to 'Live' folder
	ls $SORT_FOLDER/iPhone | \
		cut -f1 -d. | \
		uniq -d | \
		xargs -i echo $SORT_FOLDER/iPhone/{}.MOV | \
		xargs -i mv {} $LIVE_FOLDER
	
	# Rename live photos based on original photo's original date taken
	rmdir --ignore-fail-on-non-empty $SORT_FOLDER/Live
	if [ -d $LIVE_FOLDER ] 
	then
		
		exiftool -csv -ext jpg -FileName -CreateDate \
			-d %Y-%m-%d_%H.%M.%S $SORT_FOLDER/iPhone > $SORT_FOLDER/iPhone/rename.csv
		cut -d , -f 2-3 $SORT_FOLDER/iPhone/rename.csv | \
			sed 's|,| |g' | \
			sed '/FileName/d' | \
			sed -r "s|(\S+)\.\w+ (\S+)|$LIVE_FOLDER/\1.MOV $LIVE_FOLDER/\2\.MOV|gI" | \
			xargs -n2 sh -c '[ -f $0 ] && mv $0 $1'
		rm -f $SORT_FOLDER/iPhone/rename.csv
	fi

	# Rename photos based on original date taken
	exiftool -ext jpg '-FileName<${CreateDate}_${filename;$_=substr($_,4,4)}.%e' \
		-d %Y-%m-%d_%H.%M.%S $SORT_FOLDER/iPhone
	exiftool -ext png '-FileName<${DateCreated}_${filename;$_=substr($_,4,4)}.%e' \
		-d %Y-%m-%d_%H.%M.%S $SORT_FOLDER/iPhone

	# Rename videos based on Apple original date taken
	ls $SORT_FOLDER/iPhone/*.MOV | \
		xargs -i sh -c 'echo {} $(mediainfo {} | \
		grep com.apple.quicktime.creationdate | \
		sed -r "s/.*: (.*)+.*$/\1/g" | \
		xargs -I {} date -d {} +%Y-%m-%d_%H.%M.%S) | \
		sed -r "s|(\S+) (\S+)|\1 $SORT_FOLDER/iPhone/\2.MOV|g"' | \
		xargs -n 2 mv

	# Attempt to remove indexes from files that have them
	# Do not rename files if file with the same timestamp already exists
	find $SORT_FOLDER/iPhone -mindepth 1 -maxdepth 1 \
		-type f -regextype posix-egrep -regex ".*/.*" | \
		sed -r "s|(.*)/$TIMESTAMP_PATTERN_FINAL(.*)_([0-9]{4})(.*)|\1/\2_\3\4 \1/\2\4|g" | \
		xargs -n2 mv -n

	# Move all that do not match expected timestamp filename pattern
	find $SORT_FOLDER/iPhone -mindepth 1 -maxdepth 1 \
		-type f -regextype posix-egrep -regex ".*/$TIMESTAMP_PATTERN_FINAL.*" | \
		xargs -i mv -i {} $SORT_FOLDER/ProcessMe
	
	# Move timestamped files to main sort folder safely
	find $SORT_FOLDER/iPhone -mindepth 1 -exec mv -n {} $SORT_FOLDER \; 2>/dev/null
fi

### CLEAN UP ###
# Move files left behind to folder for further processing and cleanup
[ -d $SORT_FOLDER/Camera ] && find $SORT_FOLDER/Camera -mindepth 1 \
	-exec mv -n {} $SORT_FOLDER/ProcessMe \; 2>/dev/null
[ -d $SORT_FOLDER/iPhone ] && find $SORT_FOLDER/iPhone -mindepth 1 \
	-exec mv -n {} $SORT_FOLDER/ProcessMe \; 2>/dev/null

rmdir --ignore-fail-on-non-empty \
	$SORT_FOLDER/Camera \
	$SORT_FOLDER/iPhone/Live \
	$SORT_FOLDER/iPhone \
	$SORT_FOLDER/Live \
	$SORT_FOLDER/ProcessMe \
	$SORT_FOLDER \
	2>/dev/null

# Update script's store of last run timestamp
sed -r -i "s|^LAST_EXPORT=.*|LAST_EXPORT='$THIS_EXPORT'|g" ${BASH_SOURCE[0]}

