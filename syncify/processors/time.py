from datetime import timedelta
from typing import SupportsInt, Any

from dateutil.relativedelta import relativedelta

from syncify.abstract.processor import DynamicProcessor
from syncify.processors.decorators import dynamicprocessormethod


class TimeMapper(DynamicProcessor):
    """Map of time character representation to it unit conversion from seconds"""

    @classmethod
    def _processor_method_fmt(cls, name: str) -> str:
        return name.casefold().strip()[0]

    def __init__(self, func: str):
        DynamicProcessor.__init__(self)
        self._set_processor_name(func)

    def __call__(self, value: SupportsInt):
        return self._process(value)

    @dynamicprocessormethod
    def hours(self, value: SupportsInt) -> timedelta:
        """Map given ``value`` in hours to :py:class:`timedelta`"""
        return timedelta(hours=int(value))

    @dynamicprocessormethod
    def days(self, value: SupportsInt) -> timedelta:
        """Map given ``value`` in days to :py:class:`timedelta`"""
        return timedelta(days=int(value))

    @dynamicprocessormethod
    def weeks(self, value: SupportsInt) -> timedelta:
        """Map given ``value`` in weeks to :py:class:`timedelta`"""
        return timedelta(weeks=int(value))

    @dynamicprocessormethod
    def months(self, value: SupportsInt) -> relativedelta:
        """Map given ``value`` in months to :py:class:`timedelta`"""
        return relativedelta(months=int(value))

    def as_dict(self) -> dict[str, Any]:
        return {"function": self._processor_name}
