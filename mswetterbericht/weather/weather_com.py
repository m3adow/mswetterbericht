import re

from bs4 import BeautifulSoup

from mswetterbericht.lib.web import resilient_request

#####
# Note for potential future usage:
# wetter.com uses similar wording to Openweathermap (maybe they even use the service)
#####

# TODO: Maybe there's a more elegant solution than to hardcode stuff
# Hardcode some stuff as the module should be self-contained
# Hopefully there are not too many transformers
location_url = "https://www.wetter.com/deutschland/dachsenhausen/DE0001902.html"
transformers = {
    "nebel": "nebelig",
    "leichter_regen_und_windig": "leicht regnerisch und windig",
    "leichter_regenschauer_und_windig": "leicht schauerig und windig",
}


def prettify_forecast(forecast: set, weather_transformers: dict) -> str:
    """
    "Prettify" a set of scraped strings from the weather provider
    @param forecast:  The set of raw scraped strings
    @param weather_transformers: "Weather transformers" used to create a better wording for the forecast
    @return: Returns a (hopefully) nicely worded string for the weather forecast
    """
    pretty_forecast_set = set()
    for weather in forecast:
        # Remove all but one whitespace between words
        weather = re.sub(r"\s+", " ", weather)
        sanitised_weather = weather.replace(" ", "_").lower()
        # Add transformed word if matches
        if pretty_weather := weather_transformers.get(sanitised_weather):
            pretty_forecast_set.add(pretty_weather)
        else:
            pretty_forecast_set.add(weather)
    pretty_forecast = " und ".join(pretty_forecast_set)
    # Replace all occurences of "und" with commas except the last one
    und_count = pretty_forecast.count("und")
    return pretty_forecast.replace(" und", ",", und_count - 1)


def get_weather_forecast(location_url: str) -> set:
    """
    Scrape the weather provider for the forecast
    @param location_url: Location URL where to scrape from
    @return: Returns a set of the noon and evening forceast
    """
    r = resilient_request(location_url)
    soup = BeautifulSoup(r.text, "html.parser")
    # Not all TDs have the same class, therefore use 'select'
    mydivs = soup.select("td.text--center.delta.portable-pb")

    # Only use the two middle rows for forecast, use set for uniqueness, filter empty fields
    return set(filter(None, [div_content.text.strip() for div_content in mydivs[1:3]]))


def create_weather_forecast() -> tuple:
    """
    Coordinating function for scraping and prettifying weather forecast results
    @return: Returns a tuple with the first item being the pretty forecast string and the second being the scraped URL
    """
    forecast = get_weather_forecast(location_url)
    return prettify_forecast(forecast, transformers), location_url
