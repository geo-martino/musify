from datetime import timedelta
from typing import SupportsInt, Any

from dateutil.relativedelta import relativedelta

from syncify.processor.base import DynamicProcessor
from syncify.processor.decorators import dynamicprocessormethod


class TimeMapper(DynamicProcessor):
    """Map of time character representation to it unit conversion from seconds"""

    @classmethod
    def _processor_method_fmt(cls, name: str) -> str:
        return name.casefold().strip()[0]

    def __init__(self, func: str):
        super().__init__()
        self._set_processor_name(func)

    def __call__(self, value: SupportsInt):
        return self._process(value)

    @dynamicprocessormethod
    def hours(self, value: SupportsInt) -> timedelta:
        return timedelta(hours=int(value))

    @dynamicprocessormethod
    def days(self, value: SupportsInt) -> timedelta:
        return timedelta(days=int(value))

    @dynamicprocessormethod
    def weeks(self, value: SupportsInt) -> timedelta:
        return timedelta(weeks=int(value))

    @dynamicprocessormethod
    def months(self, value: SupportsInt) -> relativedelta:
        return relativedelta(months=int(value))

    def as_dict(self) -> dict[str, Any]:
        return {"function": self._processor_name}
