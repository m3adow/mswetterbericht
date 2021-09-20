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
error_prose_line = '* [{name}]({url}) {verb} **unverständlich/fehlerhaft**: **{pct_change}** (Kurs: {absolute_value}).'
special_prose_line = '* [{name}]({url}) {verb} **{word_change}**. Der Preis liegt bei **{abs_value}** was einer' \
                     ' Veränderung von **{pct_change}** zum Vortag entspricht.'

random.seed()


def bond_commodities_filter(soup: BeautifulSoup) -> tuple:
    mydiv = soup.find('div', {'class': 'top bold inlineblock'})
    spans = mydiv.find_all('span')
    pct_change = spans[-1].contents[0] # Percentage change
    absolute_value = spans[0].contents[0]
    return pct_change, absolute_value


def index_filter(soup: BeautifulSoup) -> tuple:
    pct_span = soup.find('span', {'data-test': 'instrument-price-change-percent'})
    # Differentiate between negative and positive values due to differing formatting
    if pct_span.contents[2] == '+':
        pct_change = '+' + pct_span.contents[4] + '%'
    else:
        pct_change = pct_span.contents[2] + '%'

    absolute_value = soup.find('span', {'data-test': 'instrument-price-last'}).contents[0]

    return pct_change, absolute_value


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
    url = 'https://www.onvista.de/derivate/index-und-partizipations-zertifikate/' + \
          'OPEN-END-ROHSTOFF-ZERTIFIKAT-AUF-ICE-ECX-EUA-FUTURES-ECF-IPE-20210628-DE000CU3RPS9'

    r = requests.get(url, headers=headers)
    if r.status_code != 200:
        print("Got HTTP %s." % r.status_code)
    soup = BeautifulSoup(r.text, 'html.parser')
    mydiv = soup.find('div', {'id': 'bid', 'class': 'five wide column'})

    price_raw = mydiv.find('span', {'class': 'price'}).contents[0]
    price = re.match(r'\d+,\d+', price_raw)[0]

    change = mydiv.find('span', {'class': 'performance-pct'}).contents[0]

    # Change comma to dot before returning
    return [price, change.replace(',', '.')]


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
    for name, url, verb, pct_change, absolute_value in investing_results:
        # investing.com does return some strange issues sometimes
        try:
            investing_lines.append(investing_prose_line.format(
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
    ('Schatzkisten', 'sind', 'https://www.investing.com/rates-bonds/u.s.-10-year-bond-yield', bond_commodities_filter),
    ('🦡 Zukünfte', 'sind', 'https://www.investing.com/indices/germany-30-futures', index_filter),
    ('💦🦡 Zukünfte', 'sind', 'https://www.investing.com/indices/nq-100-futures', index_filter),
    ('🕵️ Zukünfte', 'sind', 'https://www.investing.com/indices/us-spx-500-futures', index_filter),
    ('🐘 2000 Zukünfte', 'sind', 'https://www.investing.com/indices/smallcap-2000-futures', index_filter),
    ('Der Nikkei', 'ist', 'https://www.investing.com/indices/japan-ni225', index_filter),
    ('Der Hang Seng', 'ist', 'https://www.investing.com/indices/hang-sen-40', index_filter),
    ('🔥🛢 Zukünfte', 'sind', 'https://www.investing.com/commodities/brent-oil', bond_commodities_filter),
)

special_values = (
    ('Der Stückmünzenkurs', 'ist', 'https://www.coingecko.com/en/coins/bitcoin', bitcoin_change),
    ('CO2 Zertifikate', 'sind',
     'https://www.onvista.de/derivate/index-und-partizipations-zertifikate/' +
     'OPEN-END-ROHSTOFF-ZERTIFIKAT-AUF-ICE-ECX-EUA-FUTURES-ECF-IPE-20210628-DE000CU3RPS9', co2_change)
)


investing_results = []
for name, verb, url, filter_function in investing_values:
    r = requests.get(url, headers=headers)
    if r.status_code != 200:
        print("Got HTTP %s for '%s'. Skipping." % (r.status_code, name))
    soup = BeautifulSoup(r.text, 'html.parser')
    pct_change, absolute_value = filter_function(soup)
    investing_results.append([name, url, verb, pct_change, absolute_value])

special_results = []
for name, verb, url, filter_function in special_values:
    filter_result = filter_function()
    special_results.append([name, url, verb] + [filter_result])

print(generate_prose(investing_results, special_results))

