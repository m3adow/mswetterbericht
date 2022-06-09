import json
import random
import re
import sys
from dataclasses import dataclass
from typing import Callable

import requests
import upsidedown
from bs4 import BeautifulSoup
from requests.adapters import HTTPAdapter, Retry

# Globals
headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:91.0) Gecko/20100101 Firefox/91.0'}
url_retries = 2
closed_string = 'geschlossen'
prose = {
    'template': 'Guten Morgen zusammen, die heutige Wettervorhersage für alle, <<hier könnte Ihr Spruch stehen>>:\n\n'
                '{prose_lines}\n'
                '* [Die Wettervorhersage](https://www.wetter.com/deutschland/dachsenhausen/DE0001902.html) für'
                ' Dachsenhausen sagt einen **DASMUSSMANUELLEINGETRAGENWERDEN** Tag voraus.\n\n'
                'Und natürlich die Miesmuschel: !mm Wird heute ein grüner Tag?\n\n',
    'investing': '* [{name}]({url}) {verb} **{word_change}**, mit **{pct_change}** (Kurs: {absolute_value}).',
    'closed': '* [{name}]({url}) {verb} bei Marktschluss **{word_change}** gewesen, mit '
              '**{pct_change}** (Kurs: {absolute_value}).',
    'error': '* [{name}]({url}) {verb} **unverständlich/fehlerhaft**: **{pct_change}** (Kurs: {absolute_value}).',
    'special': '* [{name}]({url}) {verb} **{word_change}**. Der Preis liegt bei **{absolute_value}** was einer '
               'Veränderung von **{pct_change}** zum Vortag entspricht.',
    # Tuple of strings and a bool to signal upsidedown writing, note the different order, as upsidedown writing
    # is read from right to left while the formatting strings have to be ordered from left to right
    'upsidedown': {
        'investing': [
            ('* ', False), (' {verb} **{word_change}**, mit **{pct_change}** (Kurs: {absolute_value}).', True),
            ('[', False), ('{name}', True), (']({url})', False)
        ],
        'closed': [('* ', False), (
            ' {verb} bei Marktschluss **{word_change}** gewesen, mit **{pct_change}** (Kurs: {absolute_value}).', True),
                   ('[', False), ('{name}', True), (']({url})', False),

                   ]
    }
}

# Seed RNG
random.seed()


# Todo: Create a prototype class which is then used for each instrument type
@dataclass
class TradingInstrument:
    """Class for all Trading Instruments used in the forecast."""
    name: str
    verb: str
    url: str
    filter_function: Callable
    upsidedown: bool = False
    is_special: bool = False
    # These will not be filled at declaration time
    pct_change: str = None
    absolute_value: str = None
    is_closed: bool = False
    prose_line: str = 'REPLACEMEDADDY'

    def generate_prose_line(self, prose_json: dict):
        self.prose_line = ''
        # Pasta pasta?
        if self.is_special:
            # Special instruments do not have closed lines
            prose_dict = prose_json['special']
            prose_line_key = 'special'
        else:
            prose_dict = prose_json['futures']
            prose_line_key = 'investing'
            if self.is_closed:
                prose_line_key = 'closed'

        # Investing.com returns are sometimes faulty
        try:
            if self.upsidedown:
                for mystring, needs_transformation in prose['upsidedown'][prose_line_key]:
                    addstring = mystring.format(name=self.name, url=self.url, verb=self.verb,
                                                word_change=self.evaluate_change(prose_dict),
                                                absolute_value=self.absolute_value,
                                                pct_change=self.pct_change
                                                )
                    if needs_transformation:
                        self.prose_line += upsidedown.transform(addstring)
                    else:
                        self.prose_line += addstring
            else:
                self.prose_line = prose[prose_line_key].format(name=self.name, url=self.url, verb=self.verb,
                                                               word_change=self.evaluate_change(prose_dict),
                                                               absolute_value=self.absolute_value,
                                                               pct_change=self.pct_change
                                                               )
        except ValueError:
            self.prose_line = prose['error'].format(
                name=self.name, url=self.url, verb=self.verb, pct_change=self.pct_change,
                absolute_value=self.absolute_value
            )

    def generate_normal_line(self, prose_line: str, prose_json: dict) -> None:
        # investing.com returns do have some strange issues sometimes
        try:
            self.prose_line = prose_line.format(name=self.name, url=self.url, verb=self.verb,
                                                word_change=self.evaluate_change(prose_json),
                                                absolute_value=self.absolute_value, pct_change=self.pct_change
                                                )
        except ValueError:
            self.prose_line = prose['error'].format(
                name=self.name, url=self.url, verb=self.verb, pct_change=self.pct_change,
                absolute_value=self.absolute_value
            )

    def generate_upsidedown_line(self, prose_line: str, prose_json: dict) -> str:
        pass

    def evaluate_change(self, prose_dict: dict) -> str:
        change = float(self.pct_change.rstrip('%'))

        if change > 0:
            color = random.choice(prose_dict['green'])
        elif change < 0:
            color = random.choice(prose_dict['red'])
        else:
            return random.choice(prose_dict['unchanged'])

        if abs(change) >= 1.0:
            return random.choice(prose_dict['prefixes']['heavy']) + color
        elif abs(change) > 0.1:
            return color
        else:
            return random.choice(prose_dict['prefixes']['light']) + color


def bond_filter(soup: BeautifulSoup) -> tuple:
    mydiv = soup.find('div', {'class': 'top bold inlineblock'})
    spans = mydiv.find_all('span')
    pct_change = spans[-1].contents[0]  # Percentage change
    absolute_value = spans[0].contents[0]
    # Has to return a boolean as third param due to compatibility with other filters
    return pct_change, absolute_value, False


def index_commodities_filter(soup: BeautifulSoup) -> tuple:
    is_closed = False
    pct_span = soup.find('span', {'data-test': 'instrument-price-change-percent'})
    # Differentiate between negative and positive values due to differing formatting
    if pct_span.contents[2] == '+':
        # noinspection PyTypeChecker
        pct_change = '+' + pct_span.contents[4] + '%'
    else:
        pct_change = pct_span.contents[2] + '%'

    absolute_value = soup.find('span', {'data-test': 'instrument-price-last'}).contents[0]

    # Check if exchange is closed
    overdiv = soup.find('div', {'data-test': 'instrument-header-details'})
    myreg = re.compile(r'.*instrument-metadata_text__.*')
    metadata_divs = overdiv.find_all('span', {'class': myreg})
    if metadata_divs[1].contents[0] == 'Closed':
        is_closed = True
    return pct_change, absolute_value, is_closed


def bitcoin_change() -> list:
    coingecko_api_endpoint = 'https://api.coingecko.com/api/v3'

    coin_data_path = '/coins/'
    coin = 'bitcoin'
    currency = 'usd'
    params = {'tickers': False, 'market_data': True, 'community_data': False, 'developer_data': False,
              'sparkline': False}
    data = requests.get(
        coingecko_api_endpoint + coin_data_path + coin, params=params
    )
    pct_change = str(round(data.json()['market_data']['price_change_percentage_24h'], 2))

    # Coingecko does not prefix a '+'
    if float(pct_change) > 0:
        pct_change = '+' + pct_change
    price = data.json()['market_data']['current_price'][currency]
    price_data = [
        "${:,}".format(price),  # prettifies number with comma and dollar symbol
        pct_change + '%'
    ]
    return list(price_data)


def co2_change() -> list:
    url = 'https://www.onvista.de/derivate/Index-Zertifikate/158135999-CU3RPS-DE000CU3RPS9'

    r = requests.get(url, headers=headers)
    if r.status_code != 200:
        print("Got HTTP %s." % r.status_code)
    soup = BeautifulSoup(r.text, 'html.parser')
    mydiv = soup.find('div', {'class': 'flex-layout flex-layout__align-items--baseline ov-flex-layout--column-sm '
                                       'text-size--xlarge'})
    price_raw = mydiv.find('data', {'class': 'text-nowrap text-weight--medium outer-spacing--xsmall-right'}).contents[0]
    # Change comma to dot, round to two digits (removing trailing zero) and add Euro sign
    price = round(float(price_raw.replace(',', '.')), 2)
    pretty_price = str(price) + 'EUR'

    # Differentiate between positive and negative change
    # Maybe change to conditional?
    try:
        change = mydiv.find('data', {'class': 'color--cd-positive text-nowrap outer-spacing--xsmall-right'}).contents[0]
    except AttributeError:
        change = mydiv.find('data', {'class': 'color--cd-negative text-nowrap outer-spacing--xsmall-right'}).contents[0]
    pretty_change = change.replace(',', '.') + '%'

    # Change comma to dot before returning
    return [pretty_price, pretty_change]


def generate_prose(instruments: list, prose_json: dict) -> str:
    prose_lines = []
    for instrument in instruments:
        instrument.generate_prose_line(prose_json)
        prose_lines.append(instrument.prose_line)
    return prose['template'].format(prose_lines='\n'.join(prose_lines))


# Instrument definitions
investing_values = (
    ('Schatzkisten', 'sind', 'https://www.investing.com/rates-bonds/u.s.-10-year-bond-yield', bond_filter),
    ('🦡 Zukünfte', 'sind', 'https://www.investing.com/indices/germany-30-futures', index_commodities_filter),
    ('💦🦡 Zukünfte', 'sind', 'https://www.investing.com/indices/nq-100-futures', index_commodities_filter),
    ('🕵️ Zukünfte', 'sind', 'https://www.investing.com/indices/us-spx-500-futures', index_commodities_filter),
    ('DAU Johannes Zukünfte', 'sind', 'https://www.investing.com/indices/us-30-futures', index_commodities_filter),
    ('🐘 2000 Zukünfte', 'sind', 'https://www.investing.com/indices/smallcap-2000-futures', index_commodities_filter),
    ('Ⓜ🦡️Zukünfte', 'sind', 'https://www.investing.com/indices/germany-mid-cap-50-futures', index_commodities_filter),
    ('🇪🇺🦯 Zukünfte', 'sind', 'https://www.investing.com/indices/eu-stocks-50-futures', index_commodities_filter),
    ('Der ☑🦈', 'ist', 'https://www.investing.com/indices/japan-ni225', index_commodities_filter),
    ('Der Hang Seng', 'ist', 'https://www.investing.com/indices/hang-sen-40', index_commodities_filter),
    # ASX will be written upsidedown
    ('Der ASX 200', 'ist', 'https://www.investing.com/indices/aus-200', index_commodities_filter, True),
    ('🔥🛢 Zukünfte', 'sind', 'https://www.investing.com/commodities/brent-oil', index_commodities_filter),
    ('🥇 Zukünfte', 'sind', 'https://www.investing.com/commodities/gold', index_commodities_filter),
    ('🌎💨 Zukünfte', 'sind', 'https://www.investing.com/commodities/natural-gas', index_commodities_filter)
)

special_values = (
    ('Der Stückmünzenkurs', 'ist', 'https://www.coingecko.com/en/coins/bitcoin', bitcoin_change),
    ('CO2 Zertifikate', 'sind',
     'https://www.onvista.de/derivate/Index-Zertifikate/158135999-CU3RPS-DE000CU3RPS9', co2_change)
)

# Use prose.json by default
if len(sys.argv) >= 2:
    myfile = sys.argv[1]
else:
    myfile = 'prose.json'

with open(myfile, encoding='utf8') as f:
    prose_json = json.load(f)

investing_objects = [TradingInstrument(*instrument) for instrument in investing_values]
special_objects = [TradingInstrument(*instrument) for instrument in special_values]

for instrument in investing_objects:
    # Implement retries, as investing.com acts strange sometimes
    retry = Retry(total=url_retries, backoff_factor=1, status_forcelist=[502, 503, 504])
    http_adapter = HTTPAdapter(max_retries=retry)
    http_session = requests.Session()
    http_session.mount(instrument.url, http_adapter)
    r = http_session.get(instrument.url, headers=headers)
    if r.status_code != 200:
        print("Failed to get '%s'. Aborting." % instrument.name)
        exit(1)
    soup = BeautifulSoup(r.text, 'html.parser')
    instrument.pct_change, instrument.absolute_value, instrument.is_closed = instrument.filter_function(soup)

for instrument in special_objects:
    instrument.absolute_value, instrument.pct_change = instrument.filter_function()

print(generate_prose(investing_objects + special_objects, prose_json))
