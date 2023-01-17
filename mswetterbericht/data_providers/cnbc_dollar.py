import logging
import attr

from mswetterbericht.data_providers.cnbc import (
    ProviderInstrument as CNBCProviderInstrument,
)
from mswetterbericht.wetterbericht import InstrumentValues


logger = logging.getLogger(__name__)


@attr.define(kw_only=True)
class DollarValues(InstrumentValues):
    @property
    def pretty_absolute_value(self) -> str:
        """Prettify absolute_value with additional Dollar symbol"""
        return f"${super().pretty_absolute_value}"


@attr.define(kw_only=True)
class ProviderInstrument(CNBCProviderInstrument):
    """CNBC ProviderInstrument with absolute_value in $$$"""

    @classmethod
    def from_instrument_data(cls, instrument_data: dict):
        myclass = super().from_instrument_data(instrument_data)
        myclass.values = DollarValues(
            pct_change=myclass.values.pct_change,
            absolute_value=myclass.values.absolute_value,
        )
        return myclass
