from mswetterbericht.lib.web import resilient_request
import requests
from bs4 import BeautifulSoup

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
}


def prettify_forecast(forecast: set, weather_transformers: dict) -> str:
    pretty_forecast = set()
    for weather in forecast:
        sanitised_weather = weather.replace(" ", "_").lower()
        if pretty_weather := weather_transformers.get(sanitised_weather):
            pretty_forecast.add(pretty_weather)
        else:
            pretty_forecast.add(weather)
    return " und ".join(pretty_forecast)


def get_weather_forecast(location_url: str) -> set:
    r = resilient_request(location_url)
    soup = BeautifulSoup(r.text, "html.parser")
    # Not all TDs have the same class, therefore use 'select'
    mydivs = soup.select("td.text--center.delta.portable-pb")

    # Only use the two middle rows for forecast, use set for uniqueness, filter empty fields
    return set(filter(None, [div_content.text.strip() for div_content in mydivs[1:3]]))


def create_weather_forecast() -> list:
    forecast = get_weather_forecast(location_url)
    return [prettify_forecast(forecast, transformers), location_url]
