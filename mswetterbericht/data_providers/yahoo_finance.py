from mswetterbericht.wetterbericht import Instrument

import attr
import yfinance as yf


@attr.define(kw_only=True)
class ProviderInstrument(Instrument):
    """Yahoo Finance ProviderInstrument"""

    symbol: str

    @classmethod
    def from_instrument_data(cls, instrument_data: dict):
        """Create a ProviderInstrument by querying Yahoo Finance and calculating required values"""
        ticker = yf.Ticker(instrument_data["symbol"])
        current_price = ticker.info["regularMarketPrice"]
        old_price = ticker.info["regularMarketPreviousClose"]
        pct_change = round((((current_price - old_price) / old_price) * 100), 2)

        instrument_values = super().create_values(
            pct_change=pct_change, absolute_value=current_price
        )

        return cls(**instrument_data, values=instrument_values)
