import attr
import upsidedown

from mswetterbericht.data_providers.investing_com_investiny import (
    ProviderInstrument as InvestingDotComProviderInstrument,
)
from mswetterbericht.wetterbericht import InstrumentLine


@attr.define(kw_only=True)
class UpsideDownLine(InstrumentLine):
    # Takes a list of strings, every second one will be transformed upside down
    line: list

    def generate_line(self, change_word: str, **kwargs) -> str:
        """
        @param change_word: Prose word for the change
        @param kwargs: Remaining required argument for creating a line, depending on instrument type
        @return: A properly filled and formatted instrument line
        """
        new_line = self.line.copy()
        for i, item in enumerate(new_line):
            new_item = item.format(verb=self.verb, change_word=change_word, **kwargs)
            # Transform every second item
            if i % 2 == 1:
                new_line[i] = upsidedown.transform(new_item)
            else:
                new_line[i] = new_item

        return "".join(new_line)


@attr.define(kw_only=True)
class ProviderInstrument(InvestingDotComProviderInstrument):
    """Yahoo Finance ProviderInstrument with absolute_value in $$$"""

    @staticmethod
    def create_line(line: list, plural: bool) -> InstrumentLine:
        """Create an InstrumentLine object

        Only required to be easily callable or overridable from modules"""
        return UpsideDownLine(line=line, plural=plural)
