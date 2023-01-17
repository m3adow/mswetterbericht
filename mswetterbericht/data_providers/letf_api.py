import logging
import re

import attr

from mswetterbericht.lib.web import resilient_request
from mswetterbericht.wetterbericht import (
    Instrument,
    InstrumentValues,
    InstrumentLine,
    ProseGenerator,
)

logger = logging.getLogger(__name__)

api_base_path = "https://ed8boq.deta.dev/v1/overview/"

# Explicitly request JSON responses, just to be 100% safe
additional_headers = {"Accept": "application/json", "Content-Type": "application/json"}


@attr.define(kw_only=True)
class LETFInstrumentLine(InstrumentLine):
    # Default change_word as we're not using it here
    def generate_line(self, change_word: str = "", **kwargs) -> str:
        return self.line.format(**kwargs)


@attr.define(kw_only=True)
class LETFInstrumentValues(InstrumentValues):
    """LETF ProviderInstrumentValues"""

    sma_difference: float
    crosses: list
    crosses_prose: dict = attr.field(
        init=False,
        # If this changes frequently (unlikely), it should be added to the prose file
        default={
            "no_cross": "keine ✝️igung",
            "is_sma200_cross": "eine SMA200✝️igung",
            "is_sma220_cross": "eine SMA220✝️igung",
            "is_golden_cross": "eine 👑✝️igung",
            "is_death_cross": "eine ☠️✝️igung",
        },
    )

    @classmethod
    def for_lev_etf(cls, absolute_value, sma_difference, crosses):
        # pct_change is not needed, so fill it with bougus data
        pct_change = -1337
        return cls(
            pct_change=pct_change,
            absolute_value=absolute_value,
            sma_difference=sma_difference,
            crosses=crosses,
        )

    @property
    def pretty_sma_difference(self) -> str:
        """Prettify sma_difference with comma as thousands separator and removing fractional points as well as a
        potential presing"""
        return "{:,}".format(abs(int(self.sma_difference)))

    @property
    def pretty_absolute_value(self) -> str:
        """Prettify absolute_value with comma as thousands separator"""
        return "{:,}".format(int(self.absolute_value))

    @property
    def pretty_crosses(self) -> str:
        if not self.crosses:
            return self.crosses_prose["no_cross"]
        cross_prose = [self.crosses_prose[cross] for cross in self.crosses]
        # I doubt there will ever be two crosses (not sure if even possible), so don't invest effort
        return " & ".join(cross_prose)


@attr.define(kw_only=True)
class ProviderInstrument(Instrument):
    """LETF API ProviderInstrument"""

    symbol: str
    sma_type: str
    values: LETFInstrumentValues
    line: LETFInstrumentLine

    @classmethod
    def from_instrument_data(cls, instrument_data):
        """Create a ProviderInstrument by using the LETF API"""
        current_value, sma_difference, crosses = get_letf_data(
            instrument_data["symbol"], instrument_data["sma_type"]
        )
        instrument_values = cls.create_values(
            absolute_value=current_value, sma_difference=sma_difference, crosses=crosses
        )
        return cls(**instrument_data, values=instrument_values)

    @staticmethod
    def create_values(
        absolute_value: float,
        sma_difference: float,
        crosses: list,
    ) -> LETFInstrumentValues:
        """Create an InstrumentValues object

        Only required to be easily callable or overridable from modules"""
        return LETFInstrumentValues.for_lev_etf(
            absolute_value=absolute_value,
            sma_difference=sma_difference,
            crosses=crosses,
        )

    @staticmethod
    def create_line(**kwargs) -> LETFInstrumentLine:
        """Create an UpsideDownLine object"""
        return LETFInstrumentLine(**kwargs)

    def generate_prose_line(self, prose_generator: ProseGenerator) -> str:
        """Generate a nicely worded and formatted line of the instruments forecast"""
        return self.line.generate_line(
            description=self.description,
            absolute_value=self.values.pretty_absolute_value,
            sma_difference=self.values.pretty_sma_difference,
            sma_type=self.sma_type,
            crosses=self.values.pretty_crosses,
        )


def get_letf_data(instrument_symbol, sma_type) -> tuple:
    r = resilient_request(api_base_path + instrument_symbol)
    r_json = r.json()
    absolute_value = r_json["current_course"]
    sma_difference = absolute_value - r_json[sma_type]

    crosses = [key for key, value in r_json.items() if key.endswith("_cross") and value]

    return absolute_value, sma_difference, crosses
