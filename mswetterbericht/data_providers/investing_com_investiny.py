from datetime import datetime, timezone
from typing import Any, Dict, List, Literal, Union
from uuid import uuid4
import cloudscraper

from investiny.config import Config

import sys
import attr
import logging

from mswetterbericht.wetterbericht import Instrument

logger = logging.getLogger(__name__)


# Monkey patch method to use cloudscraper instead of httpx
def request_to_investing_cloudscraper(
    endpoint: Literal["history", "search", "quotes", "symbols"], params: Dict[str, Any]
) -> Union[Dict[str, Any], List[Dict[str, Any]]]:
    """Sends an HTTP GET request to Investing.com API with the introduced params.

    Args:
        endpoint: Endpoint to send the request to.
        params: A dictionary with the params to send to Investing.com API.

    Returns:
        A dictionary with the response from Investing.com API.
    """
    url = f"https://tvc6.investing.com/{uuid4().hex}/0/0/0/0/{endpoint}"
    headers = {
        "Referer": "https://tvc-invdn-com.investing.com/",
        "Content-Type": "application/json",
    }
    # Taken from https://github.com/alvarobartt/investiny/issues/71
    scraper = cloudscraper.create_scraper(
        browser={"browser": "chrome", "platform": "android", "desktop": False}
    )
    # TODO: Maybe use mswetterbericht.lib.web.resilient_request
    r = scraper.get(url, params=params, headers=headers)
    if r.status_code != 200:
        raise ConnectionError(
            f"Request to Investing.com API failed with error code: {r.status_code}."
        )
    d = r.json()

    if endpoint in ["history", "quotes"] and d["s"] != "ok":
        raise ConnectionError(
            f"Request to Investing.com API failed with error message: {d['s']}."
            if "nextTime" not in d
            else (
                f"Request to Investing.com API failed with error message: {d['s']}, the"
                " market was probably closed in the introduced dates, try again with"
                f" `from_date={datetime.fromtimestamp(d['nextTime'], tz=timezone.utc).strftime(Config.date_format)}`."
            )
        )
    return d  # type: ignore


# As investiny has a function 'investiny.info' as well, we need to monkey patch this way
# Source: https://stackoverflow.com/a/22375385
investiny_info_module = sys.modules["investiny.info"]
setattr(
    investiny_info_module, "request_to_investing", request_to_investing_cloudscraper
)
logger.debug("Monkey patched investiny.info.request_to_investing.")


@attr.define(kw_only=True)
class ProviderInstrument(Instrument):
    """cnbc.com ProviderInstrument"""

    symbol: str

    @classmethod
    def from_instrument_data(cls, instrument_data):
        """Create a ProviderInstrument by scraping Investing.com"""
        investiny_request = investiny_info_module.info(instrument_data["symbol"])[
            instrument_data["symbol"]
        ]
        instrument_values = super().create_values(
            pct_change=investiny_request["chp"], absolute_value=investiny_request["lp"]
        )
        return cls(**instrument_data, values=instrument_values)


# print(ProviderInstrument.from_instrument_data({'symbol': 'Eurex:DE30'}))
