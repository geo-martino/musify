import re
from collections.abc import Iterable, Collection
from itertools import batched
from typing import Any
from webbrowser import open as webopen

from musify.processors.base import InputProcessor, ItemProcessor
from musify.shared.core.base import Item
from musify.shared.core.collection import ItemCollection
from musify.shared.core.enum import Field, Fields
from musify.shared.exception import MusifyEnumError
from musify.shared.types import UnitIterable
from musify.shared.utils import to_collection


class ItemDownloadHelper(InputProcessor, ItemProcessor):
    """
    Runs operations for helping the user to download items from given collections.

    :param urls: The template URLs for websites to open queries for.
        The given sites should contain exactly 1 '{}' placeholder into which the processor can place
        a query for the item being searched. e.g. *bandcamp.com/search?q={}&item_type=t*
    :param fields: The default fields to take from an item for use as the query string when initially opening sites.
    :param interval: The number of items to open sites for before pausing for user input.
    """

    def __init__(self, urls: UnitIterable[str], fields: UnitIterable[Field] = Fields.ALL, interval: int = 1):
        super().__init__()

        self.urls: list[str] = to_collection(urls, list)
        if fields == Fields.ALL or Fields.ALL in to_collection(fields, set):
            fields = Fields.all()
        self.fields: list[Field] = to_collection(fields, list)
        self.interval = interval

    def __call__(self, collections: UnitIterable[ItemCollection]) -> None:
        self.open_sites(collections=collections)

    def open_sites(self, collections: UnitIterable[ItemCollection]) -> None:
        """
        Run the download helper.

        Opens the formatted ``urls`` for each item in all given collections in the user's browser.
        """
        if isinstance(collections, ItemCollection):
            items = collections.items
        else:
            items = [item for coll in collections for item in coll]

        pages_total = (len(items) // self.interval) + (len(items) % self.interval > 0)
        for page, items in enumerate(batched(items, self.interval), 1):
            not_queried = self._open_sites_for_items(items=items, fields=self.fields)
            self._pause(items=items, not_queried=not_queried, page=page, total=pages_total)

    def _open_sites_for_items(self, items: Iterable[Item], fields: Iterable[Field]) -> list[Item]:
        not_queried = []
        for item in items:
            queried = self._open_sites_for_item(item=item, fields=fields)
            if not queried:
                not_queried.append(item)

        return not_queried

    def _open_sites_for_item(self, item: Item, fields: Iterable[Field]) -> bool:
        query_parts = []
        for field in fields:
            field_name = field.name.lower()
            if not hasattr(item, field_name) or getattr(item, field_name) is None:
                continue

            value = getattr(item, field_name)
            if isinstance(value, (tuple, set, list, dict)):
                value = " ".join(value)
            query_parts.append(str(value))

        query = " ".join(query_parts)
        if not query:
            self.logger.debug(f"Could not get query for item: {item.name}")
            return False

        self.logger.debug(f"Opening {len(self.urls)} URLs with query: {query}")
        for url in self.urls:
            webopen(url.format(query))

        return True

    def _pause(self, items: Iterable[Item], not_queried: Collection[Item], page: int, total: int):
        opened = len(self.urls) * (self.interval - len(not_queried))
        not_opened = f" - Could not open sites for {len(not_queried)} items. " if not_queried else ". "
        valid_fields = [
            field.name.lower() for field in Fields.all()
            if any(
                hasattr(item, field.name.lower()) and getattr(item, field.name.lower()) is not None for item in items
            )
        ]

        header = [
            f"\t\33[1;94mOpened {opened} sites" + not_opened + "You may now search for and download the items. \33[0m"
        ]
        options = {
            "<Return/Enter>": "Once you are finished with this batch, continue on to the next batch",
            "r": "Re-open all sites for the current batch of items",
            "<Fields>":
                "Re-open all sites for the current batch of items using the input list of fields, "
                "each separated by a space e.g. title artist album",
        }

        if not_queried:
            options["n <Fields>"] = (
                f"Same as above, but only open sites for the {len(not_queried)} items "
                "which sites could not be opened for"
            )
        options["h"] = "Show this dialogue again"

        current_input = "START"
        help_text = self._format_help_text(options=options, header=header)
        help_text += f"\n\t\33[90mValid fields for this batch: {" ".join(valid_fields)}\33[0m\n"

        print("\n" + help_text)
        while current_input != '':
            current_input = self._get_user_input(f"Enter ({page}/{total})")

            if current_input.casefold() == "h":  # print help text
                print("\n" + help_text)

            elif current_input.casefold() == "r":
                self._open_sites_for_items(items=items, fields=self.fields)

            elif current_input != "":
                try:
                    fields = [
                        enum for field in re.sub(r"^n ", "", current_input).split(" ")
                        for enum in Fields.from_name(field)
                    ]
                except MusifyEnumError:
                    self.logger.warning(
                        "Some fields were not recognised. "
                        f"Please only use one of the following fields: {", ".join(valid_fields)}"
                    )
                    continue
                self._open_sites_for_items(
                    items=not_queried if current_input.startswith("n ") else items, fields=fields
                )

    def as_dict(self) -> dict[str, Any]:
        return {
            "urls": self.urls,
            "fields": [field.name.lower() for field in self.fields],
            "interval": self.interval,
        }
