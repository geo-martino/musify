"""
Meta-functions for providing reports to the user based on comparisons between objects implemented in this package.
"""

import logging
from collections.abc import Iterable

from musify.local.library import LocalLibrary
from musify.shared.core.base import Item
from musify.shared.core.collection import ItemCollection
from musify.shared.core.enum import TagField, Fields, ALL_FIELDS, TagFields
from musify.shared.core.object import Library, Playlist
from musify.shared.logger import MusifyLogger, REPORT
from musify.shared.types import UnitIterable
from musify.shared.utils import align_string, get_max_width, to_collection


def report_playlist_differences(
        source: Library | Iterable[Playlist], reference: Library | Iterable[Playlist]
) -> dict[str, dict[str, tuple[Item, ...]]]:
    """
    Generate a report on the differences between two library's playlists.

    :param source: A source library object containing the source playlists, or a collection of playlists .
    :param reference: A comparative library object or collection of playlists
        containing the playlists to compare to the source's playlists.
    :return: Report on extra, missing, and unavailable tracks for the reference library.
    """
    # noinspection PyTypeChecker
    logger: MusifyLogger = logging.getLogger(__name__)
    logger.debug("Report library differences: START")

    extra: dict[str, tuple[Item, ...]] = {}
    missing: dict[str, tuple[Item, ...]] = {}
    unavailable: dict[str, tuple[Item, ...]] = {}

    source = source.playlists if isinstance(source, Library) else {pl.name: pl for pl in source}
    reference = reference.playlists if isinstance(reference, Library) else {pl.name: pl for pl in reference}
    max_width = get_max_width(source.keys())

    logger.info("\33[1;95m ->\33[1;97m Reporting on differences between libraries \33[0m")
    logger.print()
    for name, pl_source in source.items():
        pl_reference = reference.get(name, [])

        # get differences
        source_no_uri = tuple(item for item in pl_source if not item.has_uri)
        source_extra = tuple(item for item in pl_source if item not in pl_reference)
        reference_no_uri = tuple(item for item in pl_reference if not item.has_uri)
        reference_extra = tuple(item for item in pl_reference if item not in pl_source)

        extra[name] = reference_extra
        missing[name] = source_extra
        unavailable[name] = source_no_uri + reference_no_uri

        logger.report(
            f"\33[97m{align_string(name, max_width=max_width)} \33[0m|"
            f"\33[92m{len(reference_extra):>6} extra \33[0m|"
            f"\33[91m{len(source_extra):>6} missing \33[0m|"
            f"\33[93m{len(source_no_uri) + len(reference_no_uri):>6} unavailable \33[0m|"
            f"\33[94m{len(pl_source):>6} in source \33[0m"
        )

    report: dict[str, dict[str, tuple[Item, ...]]] = {
        "Source ✗ | Compare ✓": extra,
        "Source ✓ | Compare ✗": missing,
        "Items unavailable (no URI)": unavailable
    }

    logger.report(
        f"\33[1;96m{'TOTALS':<{max_width}} \33[0m|"
        f"\33[1;92m{sum(map(len, extra.values())):>6} extra \33[0m|"
        f"\33[1;91m{sum(map(len, missing.values())):>6} missing \33[0m|"
        f"\33[1;93m{sum(map(len, unavailable.values())):>6} unavailable \33[0m|"
        f"\33[1;94m{len(source):>6} playlists \33[0m"
    )
    logger.print(REPORT)
    logger.debug("Report library differences: DONE\n")
    return report


def report_missing_tags(
        collections: LocalLibrary | Iterable[ItemCollection],
        tags: UnitIterable[TagField] = TagFields.ALL,
        match_all: bool = False
) -> dict[str, dict[Item, tuple[str, ...]]]:
    """
    Generate a report on the items with a set of collections that have missing tags.

    :param collections: A collection of item collections to report on.
        If a local library is given, use the albums of the library as the collections to report on.
    :param tags: List of tags to consider missing.
    :param match_all: When True, item counts as missing tags if item is missing ``all`` of the given tags.
        When False, item counts as missing tags when missing only one of the given tags.
    :return: Report on collections by name which have items with missing tags.
    """
    # noinspection PyTypeChecker
    logger: MusifyLogger = logging.getLogger(__name__)
    logger.debug("Report missing tags: START")

    tags = to_collection(tags, set)
    tag_order = [field.name.lower() for field in ALL_FIELDS]
    # noinspection PyTypeChecker
    tag_names = set(TagField.__tags__) if Fields.ALL in tags else TagField.to_tags(tags)
    tag_names: list[str] = list(sorted(tag_names, key=lambda x: tag_order.index(x)))

    if isinstance(collections, LocalLibrary):
        collections = collections.albums
    items_total = sum(len(collection) for collection in collections)

    logger.info(
        f"\33[1;95m ->\33[1;97m "
        f"Checking {items_total} items for {'all' if match_all else 'any'} missing tags: \n"
        f"    \33[90m{', '.join(tag_names)}\33[0m"
    )

    if Fields.URI in tags or Fields.ALL in tags:
        tag_names[tag_names.index(Fields.URI.name.lower())] = "has_uri"
    if Fields.IMAGES in tags or Fields.ALL in tags:
        tag_names[tag_names.index(Fields.IMAGES.name.lower())] = "has_image"

    missing: dict[str, dict[Item, tuple[str, ...]]] = {}
    for collection in collections:
        missing_collection: dict[Item, tuple[str, ...]] = {}
        for item in collection.items:
            missing_tags: list[str] = [tag for tag in tag_names if item[tag] is None]
            if "has_uri" in missing_tags:
                missing_tags[missing_tags.index("has_uri")] = Fields.URI.name.lower()
            if "has_image" in missing_tags:
                missing_tags[missing_tags.index("has_image")] = Fields.IMAGES.name.lower()
            if all(tag in missing_tags for tag in tag_names) if match_all else missing_tags:
                missing_collection[item] = tuple(missing_tags)

        if missing_collection:
            missing[collection.name] = missing_collection

    if not missing:
        logger.debug("Report missing tags: DONE\n")
        return missing

    all_keys = {item.name for items in missing.values() for item in items}
    max_width = get_max_width(all_keys)

    # log the report
    logger.print(REPORT)
    logger.report("\33[1;94mFound the following missing items by collection: \33[0m")
    logger.print(REPORT)
    for name, result in missing.items():
        logger.report(f"\33[1;91m -> {name} \33[0m")
        for item, tags in result.items():
            n = align_string(item.name, max_width=max_width)
            logger.report(f"\33[96m{n} \33[0m| \33[93m{', '.join(tags)} \33[0m")
        logger.print(REPORT)

    missing_tags_all = {tag for items in missing.values() for tags in items.values() for tag in tags}
    logger.info(
        f"    \33[94mFound {len(all_keys)} items with "
        f"{'all' if match_all else 'any'} missing tags\33[0m: \n"
        f"    \33[90m{', '.join(sorted(missing_tags_all, key=lambda x: tag_order.index(x)))}\33[0m"
    )
    logger.print()
    logger.debug("Report missing tags: DONE\n")
    return missing
