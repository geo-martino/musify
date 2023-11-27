from collections.abc import Collection, Mapping
from typing import MutableMapping

from syncify.abstract.item import Item
from syncify.abstract.collection import Library, ItemCollection
from syncify.enums.tags import TagName
from syncify.local.library import LocalLibrary
from syncify.utils.helpers import make_list
from syncify.utils.logger import Logger, REPORT


class Report(Logger):
    """Various methods for reporting on items/collections/libraries etc."""

    def report_library_differences(self, source: Library, compare: Library) -> Mapping[str, Mapping[str, list[Item]]]:
        """
        Generate a report on the differences between two library's playlists.

        :param source: A source library object containing the source playlists.
        :param compare: A comparative library object containing the playlists to compare
            to the source library's playlists.
        :return: Report on extra, missing, and unavailable tracks for the compare library.
        """
        self.logger.debug("Report library differences: START")
        extra = {}
        missing = {}
        unavailable = {}

        max_width = self.get_max_width(source.playlists.keys())

        self.logger.info('\33[1;95m ->\33[1;97m Reporting on differences between libraries \33[0m')
        self.print_line()
        for source_playlist in source.playlists.values():
            name = source_playlist.name
            compare_playlist = compare.playlists.get(name)
            source_items = source_playlist.items
            compare_items = compare_playlist.items if compare_playlist else []

            # get differences
            source_extra = [item for item in source_items if item.has_uri and item not in compare_items]
            source_no_uri = [item for item in source_items if not item.has_uri]
            compare_extra = [item for item in compare_items if item.has_uri and item not in source_items]
            compare_no_uri = [item for item in compare_items if not item.has_uri]

            extra[name] = compare_extra
            missing[name] = source_extra
            unavailable[name] = source_no_uri + compare_no_uri

            self.logger.report(f"\33[97m{self.align_and_truncate(name, max_width=max_width)} \33[0m|"
                               f"\33[92m{len(compare_extra):>6} extra \33[0m|"
                               f"\33[91m{len(source_extra):>6} missing \33[0m|"
                               f"\33[93m{len(source_no_uri) + len(compare_no_uri):>6} unavailable \33[0m|"
                               f"\33[94m{len(source_playlist):>6} in source \33[0m")

        report = {"Source ✗ | Compare ✓": extra,
                  "Source ✓ | Compare ✗": missing,
                  "Items unavailable (no URI)": unavailable}

        self.logger.report(
            f"\33[1;96m{'TOTALS':<{max_width}} \33[0m|"
            f"\33[1;92m{sum(len(items) for items in extra.values()):>6} extra \33[0m|"
            f"\33[1;91m{sum(len(items) for items in missing.values()):>6} missing \33[0m|"
            f"\33[1;93m{sum(len(items) for items in unavailable.values()):>6} unavailable \33[0m|"
            f"\33[1;94m{len(source.playlists):>6} playlists \33[0m"
        )
        self.print_line(REPORT)
        self.logger.debug("Report library differences: DONE\n")
        return report

    def report_missing_tags(self,
                            collections: LocalLibrary | Collection[ItemCollection],
                            tags: list[TagName] = TagName.ALL,
                            match_all: bool = False) -> Mapping[ItemCollection, Mapping[Item, list[str]]]:
        """
        Generate a report on the items with a set of collections that have missing tags.

        :param collections: A collection of item collections to report on.
            If a local library is given, use the albums of the library as the collections to report on.
        :param tags: List of tags to consider missing.
        :param match_all: When True, item counts as missing tags if item is missing ``all`` of the given tags.
            When False, item counts as missing tags when missing only one of the given tags.
        :return: Report on collections by name which have items with missing tags.
        """
        self.logger.debug("Report missing tags: START")

        tags = make_list(tags)
        tag_names = set(TagName.to_tags(tags))

        if isinstance(collections, LocalLibrary):
            collections = collections.albums
        items_total = sum(len(collection) for collection in collections)
        self.logger.info(f"\33[1;95m ->\33[1;97m "
                         f"Checking {items_total} items for {'all' if match_all else 'any'} missing tags: \n"
                         f"    \33[90m{', '.join(tag_names)}\33[0m")

        if TagName.URI in tags or TagName.ALL in tags:
            tag_names.remove("uri")
            tag_names.add("has_uri")
        if TagName.IMAGES in tags or TagName.ALL in tags:
            tag_names.remove("images")
            tag_names.add("has_image")

        missing: MutableMapping[ItemCollection, Mapping[Item, list[str]]] = {}
        for collection in collections:
            missing_collection: MutableMapping[Item, list[str]] = {}
            for item in collection.items:
                missing_tags = [tag for tag in tag_names if item[tag] is None]
                if all(missing_tags) if match_all else any(missing_tags):
                    missing_collection[item] = missing_tags

            if missing_collection:
                missing[collection] = missing_collection

        if not missing:
            self.logger.debug("Report missing tags: DONE\n")
            return missing

        all_keys = [item.name for items in missing.values() for item in items]
        max_width = self.get_max_width(all_keys)

        # log the report
        self.print_line(REPORT)
        self.logger.report("\33[1;94mFound the following missing items by collection: \33[0m")
        self.print_line(REPORT)
        for collection, result in missing.items():
            self.logger.report(f"\33[1;91m -> {collection.name} \33[0m")
            for item, tags in result.items():
                name = self.align_and_truncate(item.name, max_width=max_width)
                self.logger.report(f"\33[96m{name} \33[0m| \33[93m{', '.join(tags)} \33[0m")
            self.print_line(REPORT)

        self.logger.info(f"    \33[94mFound {len(all_keys)} items with "
                         f"{'all' if match_all else 'any'} missing tags\33[0m: \n"
                         f"    \33[90m{', '.join(tag_names)}\33[0m")
        self.print_line()
        self.logger.debug("Report missing tags: DONE\n")
        return missing
