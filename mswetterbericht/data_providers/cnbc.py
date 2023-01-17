import json.decoder
import logging
import re
import xmltodict
import attr

from mswetterbericht.lib.web import resilient_request
from mswetterbericht.wetterbericht import Instrument

logger = logging.getLogger(__name__)

api_base_path = (
    "https://quote.cnbc.com/quote-html-webservice/restQuote/symbolType/symbol?symbols="
)

# Prevent the API from randomly responding with XML instead of JSON
additional_headers = {"Accept": "application/json", "Content-Type": "application/json"}

# The Regex to filter an instrument price so pre- or suffixes are removed
number_regex = re.compile(r"\d{1,3}(,\d{3})*(\.\d+)?")


@attr.define(kw_only=True)
class ProviderInstrument(Instrument):
    """cnbc.com ProviderInstrument"""

    symbol: str

    @classmethod
    def from_instrument_data(cls, instrument_data):
        """Create a ProviderInstrument by scraping Investing.com"""
        current_value, pct_change = get_price_and_change(instrument_data["symbol"])
        instrument_values = super().create_values(
            pct_change=pct_change, absolute_value=current_value
        )
        return cls(**instrument_data, values=instrument_values)


def get_price_and_change(instrument_symbol) -> list:
    # As the API occasionally responds with XML (even with the additional headers), convert the answer if it's not JSON
    r = resilient_request(
        api_base_path + instrument_symbol, additional_headers=additional_headers
    )
    try:
        r_json = r.json()["FormattedQuoteResult"]["FormattedQuote"][0]
    except json.decoder.JSONDecodeError:
        r_json = xmltodict.parse(r.text)["FormattedQuoteResult"]["FormattedQuote"]
    # Filter pre- and suffixes and remove thousands separator so the value can be converted to float
    current_value = float(number_regex.search(r_json["last"]).group().replace(",", ""))
    old_value = float(
        number_regex.search(r_json["previous_day_closing"]).group().replace(",", "")
    )

    pct_change = round((((current_value - old_value) / old_value) * 100), 2)

    return [current_value, pct_change]
