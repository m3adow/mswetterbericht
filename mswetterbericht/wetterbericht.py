import logging
from argparse import ArgumentParser, Namespace
from importlib import import_module
from random import choice as random_choice

import attr
from ruamel.yaml import YAML

# Configure logger
logging.basicConfig(
    format="%(asctime)s %(levelname)-8s %(message)s", datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

# Configure ruamel.yaml parser
yaml = YAML(typ="safe")


@attr.define(kw_only=True)
class ProseGenerator:
    """Helper class for formatting stuff"""

    properties: dict
    prefixes: dict
    the_talk: str

    @classmethod
    def from_prose_file(cls, prose_file: str):
        """Generate a class directly from a YAML formatted prose file

        @param prose_file: YAML file with prose words
        @return: ProseGenerator object
        """
        with open(prose_file) as f:
            prose_dict = yaml.load(f)
        the_talk = prose_dict["the_talk"]

        return cls(
            properties=prose_dict["properties"],
            prefixes=prose_dict["prefixes"],
            the_talk=the_talk,
        )

    def choose_change_word(self, pct_change: float, instrument_type: str) -> str:
        """Choose property and prefix depending on 'pct_change'

        @param pct_change: Percentage of change for the associated Instrument
        @param instrument_type: type of the associated instrument
        @return: Returns a prosaic description of the numerical percentage change
        """
        try:
            if pct_change > 0:
                color = random_choice(self.properties[instrument_type]["green"])
            elif pct_change < 0:
                color = random_choice(self.properties[instrument_type]["red"])
            else:
                return random_choice(self.properties[instrument_type]["unchanged"])

            if abs(pct_change) >= 1.0:
                return random_choice(self.prefixes[instrument_type]["heavy"]) + color
            elif abs(pct_change) > 0.1:
                return color
            else:
                return random_choice(self.prefixes[instrument_type]["light"]) + color
        except KeyError as e:
            logger.critical(
                f"Could not find prose for instrument type {instrument_type}."
            )
            raise e

    def talk_the_talk(self, prose_lines: list, weather_line: str) -> str:
        return self.the_talk.format(
            prose_lines="\n".join(prose_lines), weather_line=weather_line
        )


@attr.define(kw_only=True)
class InstrumentLine:
    """Class for instrument lines, used for formatting"""

    line: str = attr.field(converter=lambda x: x.strip())
    plural: bool

    @property
    def verb(self) -> str:
        """
        @return: Return either plural or singular form of the verb "sein"
        """
        if self.plural:
            return "sind"
        return "ist"

    def generate_line(self, change_word: str, **kwargs) -> str:
        """
        @param change_word: Prose word for the change
        @param kwargs: Remaining required arguments for the InstrumentLine
        @return: A properly filled and formatted instrument line
        """
        return self.line.format(verb=self.verb, change_word=change_word, **kwargs)


@attr.define
class InstrumentValues:
    pct_change: float = attr.field(converter=float)
    absolute_value: float = attr.field(converter=float)

    @property
    def pretty_pct_change(self) -> str:
        """Prettify pct_change with two decimals, percent and plus sign if required"""
        if self.pct_change > 0:
            return f"+{self.pct_change:.2f}%"
        return f"{self.pct_change:.2f}%"

    @property
    def pretty_absolute_value(self) -> str:
        """Prettify absolute_value with comma as thousands separator"""
        return "{:,}".format(self.absolute_value)


@attr.define(kw_only=True)
class Instrument:
    """Prototype Class for all trading instruments in the forecast"""

    description: str
    # Instrument type
    type: str
    # Priority for ordering of prose lines, the lower the number, the earlier it will be added
    priority: int = attr.field(converter=int)
    # Values of the instrument
    values: InstrumentValues
    # InstrumentLine object filled with the correct attributes for this Instrument
    line: InstrumentLine
    # Url of the instrument, defaulted to Rick Roll video if not provided (although it's probably never used then)
    url: str = attr.field(default="https://www.youtube.com/watch?v=dQw4w9WgXcQ")

    @classmethod
    def from_instrument_data(cls, instrument_data):
        """The intended way to create this class for child classes, has to create its own InstrumentLine object"""
        pass

    @staticmethod
    def create_values(pct_change: float, absolute_value: float) -> InstrumentValues:
        """Create an InstrumentValues object

        Only required to be easily callable or overridable from modules"""
        return InstrumentValues(pct_change=pct_change, absolute_value=absolute_value)

    @staticmethod
    def create_line(line: str, plural: bool) -> InstrumentLine:
        """Create an InstrumentLine object

        Only required to be easily callable or overridable from modules"""
        return InstrumentLine(line=line, plural=plural)

    def generate_prose_line(self, prose_generator: ProseGenerator) -> str:
        """Generate a nicely worded and formatted line of the instruments forecast"""
        change_word = prose_generator.choose_change_word(
            self.values.pct_change, self.type
        )
        return self.line.generate_line(
            change_word=change_word,
            description=self.description,
            url=self.url,
            pct_change=self.values.pretty_pct_change,
            absolute_value=self.values.pretty_absolute_value,
        )


def parse_args() -> Namespace:
    parser = ArgumentParser()
    parser.add_argument("--prose-file", required=True)
    parser.add_argument("--instruments-file", required=True)
    return parser.parse_args()


def create_instruments(instruments_data: dict) -> list:
    """Create ProviderInstrument objects by dynamically importing the provider module (key of instruments_data)"""
    defaults = instruments_data.get("defaults", {})
    instruments = []
    for data_provider, instruments_list in instruments_data["instruments"].items():
        try:
            mod = import_module(f"mswetterbericht.data_providers.{data_provider}")
            provider_instrument = getattr(mod, "ProviderInstrument")
            for instrument in instruments_list:
                # Add defaults if keys don't exist
                complete_instrument = defaults.copy()
                complete_instrument.update(instrument)

                # We may need this twice
                plural = complete_instrument.pop("plural")
                # noinspection PyBroadException
                try:
                    # Putting the creation here instead of in the modules enables internal changes without needing to
                    # change each module

                    complete_instrument["line"] = provider_instrument.create_line(
                        plural=plural,
                        line=instruments_data["lines"]["instruments"][
                            complete_instrument["type"]
                        ],
                    )
                    instruments.append(
                        provider_instrument.from_instrument_data(complete_instrument)
                    )

                # Yep, the exception being that broad is intentional
                except Exception as e:
                    logger.error(
                        f"Encountered error for "
                        f"'{complete_instrument.get('description', 'unknown instrument')}'. Error args: {e.args}"
                    )
                    # Use the error line for faulty instruments
                    complete_instrument["line"] = provider_instrument.create_line(
                        plural=plural, line=instruments_data["lines"]["error"]
                    )
                    # Create a "fake" instrument which only contains the most important details for the error line
                    instruments.append(
                        Instrument(
                            # Add the type to the description to be able to differentiate between the same instrument
                            # for different types (e.g. Futures and LETF)
                            description=f'{complete_instrument["description"]} ({complete_instrument["type"]})',
                            # Use the default type as this should contain the absolute minimum requirements
                            type=defaults["type"],
                            priority=complete_instrument["priority"],
                            values=InstrumentValues(
                                pct_change=-1337, absolute_value=-1337
                            ),
                            line=complete_instrument["line"],
                        )
                    )

        except (ModuleNotFoundError, AttributeError) as e:
            logger.error(
                f"Skipping instruments of Data Provider '{data_provider}. Error was: '{e}'"
            )
            continue
    return instruments


def create_weather_line(prose_line: str) -> str:
    """Get weather forecast and fill prose_line with it"""
    # Weather is hard coded for now
    from mswetterbericht.weather import weather_com

    forecast, url = weather_com.create_weather_forecast()
    return prose_line.format(url=url, forecast=forecast)


def forecast(instruments_file: str, prose_file: str):
    goethe = ProseGenerator.from_prose_file(prose_file)
    with open(instruments_file) as f:
        instruments_file_content = yaml.load(f)
    # Create instruments and sort by instrument priority
    instruments = sorted(
        create_instruments(instruments_file_content), key=lambda inst: inst.priority
    )
    weather_template = instruments_file_content["lines"]["weather"]

    prose_lines = [instrument.generate_prose_line(goethe) for instrument in instruments]
    weather_line = create_weather_line(weather_template)
    return goethe.talk_the_talk(prose_lines, weather_line)


if __name__ == "__main__":
    args = parse_args()
    print(forecast(instruments_file=args.instruments_file, prose_file=args.prose_file))
