"""Explicit adapter registration; merely listing a clock never enables computation."""

from ..errors import ACCError
from ..registry import Clock
from .base import ClockAdapter
from .horvath_2013 import HorvathDecimal, HorvathPython


def get_adapter(clock: Clock, implementation_id: str = "python-fsum") -> ClockAdapter:
    adapters: tuple[ClockAdapter, ...] = (HorvathPython(), HorvathDecimal())
    for adapter in adapters:
        if (
            adapter.clock_id == clock.definition.clock_id
            and adapter.implementation_id == implementation_id
            and implementation_id in clock.definition.implementation_ids
        ):
            return adapter
    raise ACCError(
        "ACC_IMPLEMENTATION_UNAVAILABLE",
        "Requested execution adapter is unavailable for this clock.",
    )


def adapter_available(clock: Clock) -> bool:
    for identifier in clock.definition.implementation_ids:
        try:
            get_adapter(clock, identifier)
            return True
        except ACCError:
            continue
    return False
