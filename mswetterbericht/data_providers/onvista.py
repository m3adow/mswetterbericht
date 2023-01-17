import logging

import attr
from bs4 import BeautifulSoup

from mswetterbericht.lib.web import resilient_request
from mswetterbericht.wetterbericht import Instrument
from mswetterbericht.wetterbericht import InstrumentValues

logger = logging.getLogger(__name__)


@attr.define(kw_only=True)
class EuroValues(InstrumentValues):
    @property
    def pretty_absolute_value(self) -> str:
        """Prettify absolute_value with additional Euro symbol"""
        return f"{super().pretty_absolute_value}€"


@attr.define(kw_only=True)
class ProviderInstrument(Instrument):
    """Onvista ProviderInstrument"""

    @classmethod
    def from_instrument_data(cls, instrument_data):
        """Create a ProviderInstrument by scraping Onvista"""
        current_price, pct_change = get_price_and_change(instrument_data["url"])
        instrument_values = EuroValues(
            pct_change=pct_change, absolute_value=current_price
        )
        return cls(**instrument_data, values=instrument_values)


def get_price_and_change(url) -> list:
    r = resilient_request(url)
    soup = BeautifulSoup(r.text, "html.parser")
    mydiv = soup.find(
        "div",
        {
            "class": "flex-layout flex-layout__align-items--baseline ov-flex-layout--column-sm "
            "text-size--xlarge"
        },
    )
    raw_price = mydiv.find(
        "data", {"class": "text-nowrap text-weight--medium outer-spacing--xsmall-right"}
    ).contents[0]

    # Differentiate between positive and negative change
    # Maybe change to conditional?
    try:
        raw_change = mydiv.find(
            "data",
            {"class": "color--cd-positive text-nowrap outer-spacing--xsmall-right"},
        ).contents[0]
    except AttributeError:
        raw_change = mydiv.find(
            "data",
            {"class": "color--cd-negative text-nowrap outer-spacing--xsmall-right"},
        ).contents[0]

    # Change comma to dot and round to two digits before returning
    return [round(float(item.replace(",", ".")), 2) for item in [raw_price, raw_change]]
