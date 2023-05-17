from typing import List, Mapping

from syncify.abstract import Item
from syncify.local.track import TagName
from syncify.abstract.collection import Library, ItemCollection
from syncify.utils.logger import Logger


class Report(Logger):
    def report_library_differences(self, source: Library, compare: Library) -> Mapping[str, Mapping[str, List[Item]]]:
        """
        Generate a report on the differences between two library's playlists.

        :param source: A source library object containing the source playlists.
        :param compare: A comparative library object containing the playlists to compare
            to the source library's playlists.
        :return: Report on extra, missing, and unavailable tracks for the compare library.
        """
        extra = {}
        missing = {}
        unavailable = {}

        max_width = self._get_max_width(source.playlists.keys(), max_width=50)

        self._logger.info('\33[1;95m ->\33[1;97m Reporting on differences between libraries... \33[0m')
        for source_playlist in source.playlists.values():
            name = source_playlist.name
            compare_playlist = compare.playlists.get(name)
            source_items = source_playlist.items
            compare_items = compare_playlist.items if compare_playlist else []

            # intersection = [item for item in compare_items if item in source_items]
            source_extra = [item for item in source_items if item.has_uri and item not in compare_items]
            source_no_uri = [item for item in source_items if not item.has_uri]
            compare_extra = [item for item in compare_items if item.has_uri and item not in source_items]
            compare_no_uri = [item for item in compare_items if not item.has_uri]

            extra[name] = compare_extra
            missing[name] = source_extra
            unavailable[name] = source_no_uri + compare_no_uri

            self._logger.info(f"{self._truncate_align_str(name, max_width=max_width)} |"
                              f"\33[92m{len(compare_extra):>4} extra \33[0m|"
                              f"\33[91m{len(source_extra):>4} missing \33[0m|"
                              f"\33[93m{len(source_no_uri) + len(compare_no_uri):>4} unavailable \33[0m")

        report = {"Source ✗ | Compare ✓": extra,
                  "Source ✓ | Compare ✗": missing,
                  "Items unavailable (no URI)": unavailable}

        self._logger.info(
            f"\33[1;96m{self._truncate_align_str('TOTALS', max_width=max_width)} \33[0m|"
            f"\33[1;92m{sum(len(items) for items in extra.values()):>4} extra \33[0m|"
            f"\33[1;91m{sum(len(items) for items in missing.values()):>4} missing \33[0m|"
            f"\33[1;93m{sum(len(items) for items in unavailable.values()):>4} unavailable \33[0m\n"
        )

        return report

    def report_missing_tags(self,
                            collections: List[ItemCollection],
                            tags: List[TagName] = TagName.ALL,
                            match_all: bool = False) -> Mapping[str, List[Item]]:
        """
        Generate a report on the items with a set of collections that have missing tags.

        :param collections: dict. Metadata in form <name>: <list of dicts of track's metadata>
        :param tags: list, default=None. List of tags to consider missing.
        :param match_all: When True, item counts as missing tags if item is missing ``all`` of the given tags.
            When False, item counts as missing tags when missing only one of the given tags.
        :return: Report on collections by name which have items with missing tags.
        """
        if tags == TagName.ALL or TagName.ALL in tags:
            tags = TagName.all()
        tag_names = [t for tag in tags for t in tag.to_tag()]
        if TagName.URI in tags:
            tag_names.append("has_uri")
        if TagName.IMAGES in tags:
            tag_names.remove("images")
            tag_names.append("has_image")

        items_total = sum(len(collection) for collection in collections)
        self._logger.info(f"Checking {items_total} items for {'all' if match_all else 'any'} missing tags: "
                          f"{', '.join(tag_names)}")

        missing_tags = {}
        for collection in collections:
            name = collection.name
            items = collection.items

            missing = []
            for item in items:
                if match_all:  # check if track is missing all tags
                    match = all(getattr(item, tag, None) is None for tag in tag_names)
                else:  # check if track is missing only some tags
                    match = any(getattr(item, tag, None) is None for tag in tag_names)

                if match:
                    missing.append(item)

            if len(missing) > 0:
                missing_tags[name] = missing

        items_count = len([item for items in missing_tags.values() for item in items])
        self._logger.info(f"\33[93mFound {items_count} items with {'all' if match_all else 'any'} missing tags\33[0m: "
                          f"{', '.join(tag_names)}")

        return missing_tags
