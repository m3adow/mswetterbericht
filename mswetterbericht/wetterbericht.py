import requests
from bs4 import BeautifulSoup
import re
import json
import random
import sys

headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:91.0) Gecko/20100101 Firefox/91.0'}
prose_template = 'Guten Morgen zusammen,  ' \
                 'die heutige Wettervorhersage für alle, <<hier könnte Ihr Spruch stehen>>:\n\n' \
                 '{prose_lines}\n' \
                 '* [Die Wettervorhersage](https://www.wetter.com/deutschland/dachsenhausen/DE0001902.html) für' \
                 ' Dachsenhausen sagt einen **DASMUSSMANUELLEINGETRAGENWERDEN** Tag voraus.\n\n' \
                 'Und natürlich die Miesmuschel: !mm Wird heute ein grüner Tag?\n\n'
investing_prose_line = '* [{name}]({url}) {verb} **{word_change}**, mit **{pct_change}** (Kurs: {absolute_value}).'
closed_prose_line = '* [{name}]({url}) {verb} bei Marktschluss **{word_change}** gewesen, mit ' \
                    '**{pct_change}** (Kurs: {absolute_value}).'
error_prose_line = '* [{name}]({url}) {verb} **unverständlich/fehlerhaft**: **{pct_change}** (Kurs: {absolute_value}).'
special_prose_line = '* [{name}]({url}) {verb} **{word_change}**. Der Preis liegt bei **{abs_value}** was einer' \
                     ' Veränderung von **{pct_change}** zum Vortag entspricht.'
closed_string = 'geschlossen'

random.seed()


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
                                       'outer-spacing--xsmall-bottom text-size--xlarge'})
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
    pretty_change = change.replace(',', '.')

    # Change comma to dot before returning
    return [pretty_price, pretty_change]


def evaluate_change(change: str, prose_dict: dict) -> str:
    change = float(change.rstrip('%'))

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


def generate_prose(investing_results, special_results) -> str:
    if len(sys.argv) >= 2:
        myfile = sys.argv[1]
    else:
        myfile = 'prose.json'

    with open(myfile, encoding='utf8') as f:
        prose_json = json.load(f)
    investing_lines = []
    for name, url, verb, pct_change, absolute_value, is_closed in investing_results:
        if is_closed:
            my_prose_line = closed_prose_line
        else:
            my_prose_line = investing_prose_line
        # investing.com does return some strange issues sometimes
        try:
            investing_lines.append(my_prose_line.format(
                name=name, url=url, verb=verb,
                word_change=evaluate_change(pct_change, prose_json['futures']), pct_change=pct_change,
                absolute_value=absolute_value
            ))
        except ValueError:
            investing_lines.append(error_prose_line.format(
                name=name, url=url, verb=verb, pct_change=pct_change, absolute_value=absolute_value
            ))
    for name, url, verb, change_list in special_results:
        investing_lines.append(special_prose_line.format(
            name=name, url=url, verb=verb, word_change=evaluate_change(change_list[1], prose_json['special']),
            abs_value=change_list[0], pct_change=change_list[1]
        ))

    return prose_template.format(prose_lines='\n'.join(investing_lines))


investing_values = (
    ('Schatzkisten', 'sind', 'https://www.investing.com/rates-bonds/u.s.-10-year-bond-yield', bond_filter),
    ('🦡 Zukünfte', 'sind', 'https://www.investing.com/indices/germany-30-futures', index_commodities_filter),
    ('💦🦡 Zukünfte', 'sind', 'https://www.investing.com/indices/nq-100-futures', index_commodities_filter),
    ('🕵️ Zukünfte', 'sind', 'https://www.investing.com/indices/us-spx-500-futures', index_commodities_filter),
    ('DAU Johannes Zukünfte', 'sind', 'https://www.investing.com/indices/us-30-futures', index_commodities_filter),
    ('🐘 2000 Zukünfte', 'sind', 'https://www.investing.com/indices/smallcap-2000-futures', index_commodities_filter),
    ('Ⓜ🦡️Zukünfte', 'sind', 'https://www.investing.com/indices/germany-mid-cap-50-futures', index_commodities_filter),
    ('🇪🇺🦯 Zukünfte', 'sind', 'https://www.investing.com/indices/eu-stocks-50-futures', index_commodities_filter),
    ('Der Nikkei', 'ist', 'https://www.investing.com/indices/japan-ni225', index_commodities_filter),
    ('Der Hang Seng', 'ist', 'https://www.investing.com/indices/hang-sen-40', index_commodities_filter),
    ('Der ASX 200', 'ist', 'https://www.investing.com/indices/aus-200', index_commodities_filter),
    ('🔥🛢 Zukünfte', 'sind', 'https://www.investing.com/commodities/brent-oil', index_commodities_filter),
    ('🥇 Zukünfte', 'sind', 'https://www.investing.com/commodities/gold', index_commodities_filter)
)

special_values = (
    ('Der Stückmünzenkurs', 'ist', 'https://www.coingecko.com/en/coins/bitcoin', bitcoin_change),
    ('CO2 Zertifikate', 'sind',
     'https://www.onvista.de/derivate/Index-Zertifikate/158135999-CU3RPS-DE000CU3RPS9', co2_change)
)

investing_results = []
for name, verb, url, filter_function in investing_values:
    r = requests.get(url, headers=headers)
    if r.status_code != 200:
        print("Got HTTP %s for '%s'. Skipping." % (r.status_code, name))
    soup = BeautifulSoup(r.text, 'html.parser')
    pct_change, absolute_value, is_closed = filter_function(soup)
    investing_results.append([name, url, verb, pct_change, absolute_value, is_closed])

special_results = []
for name, verb, url, filter_function in special_values:
    filter_result = filter_function()
    special_results.append([name, url, verb] + [filter_result])

print(generate_prose(investing_results, special_results))

