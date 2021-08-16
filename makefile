# ----------------------------------
# 		INSTALL & TEST
# ----------------------------------
install_requirements:
	@pip install -r requirements.txt

# ----------------------------------
# 		FUNCTIONS
# ----------------------------------
update_playlists:
	@python main.py update

refresh_playlists:
	@python main.py refresh

generate_report:
	@python main.py differences

add_artwork:
	@python main.py artwork

missing_artwork:
	@python main.py missing_artwork

extract_local_images:
	@python main.py extract_local

extract_spotify_images:
	@python main.py extract_spotify

check_uri:
	@python main.py check

check_uri_simple:
	@python main.py simplecheck

missing_tags:
	@python main.py missing_tags

update_tags:
	@python main.py update_tags

replace_tags:
	@python main.py update_tags refresh=True