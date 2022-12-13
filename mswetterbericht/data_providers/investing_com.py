import logging

import attr
from bs4 import BeautifulSoup

from mswetterbericht.lib.web import resilient_request
from mswetterbericht.wetterbericht import Instrument

logger = logging.getLogger(__name__)


@attr.define(kw_only=True)
class ProviderInstrument(Instrument):
    """Investing.com ProviderInstrument"""

    @classmethod
    def from_instrument_data(cls, instrument_data):
        """Create a ProviderInstrument by scraping Investing.com"""
        current_price, pct_change = get_price_and_change(instrument_data["url"])
        instrument_values = super().create_values(
            pct_change=pct_change, absolute_value=current_price
        )
        return cls(**instrument_data, values=instrument_values)


def get_price_and_change(url) -> list:
    r = resilient_request(url)
    soup = BeautifulSoup(r.text, "html.parser")
    pct_span = soup.find("span", {"data-test": "instrument-price-change-percent"})
    # Differentiate between negative and positive values due to differing formatting
    if pct_span.contents[2] == "+":
        # noinspection PyTypeChecker
        pct_change = str(pct_span.contents[4])
    else:
        pct_change = str(pct_span.contents[2])

    # Clean up value a bit to remove comma
    absolute_value = str(
        soup.find("span", {"data-test": "instrument-price-last"}).contents[0]
    ).replace(",", "")

    return [absolute_value, pct_change]
