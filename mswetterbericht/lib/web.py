import logging
from time import sleep

import cloudscraper
from requests.models import Response

logger = logging.getLogger(__name__)


def resilient_request(
    url: str, retries: int = 3, backoff_factor: int = 5, additional_headers=None
) -> Response:
    """Do requests with retries on 5XX errors"""
    if additional_headers is None:
        additional_headers = {}
    current_try = 1
    backoff_time = backoff_factor
    scraper = cloudscraper.CloudScraper(interpreter="py2js")
    scraper.headers.update(additional_headers)
    # Manually implement retries as I couldn't get the "normal" requests version working with cloudscraper
    while current_try <= retries:
        r: Response = scraper.get(url)
        if r.status_code == 200:
            break
        elif r.status_code <= 500 < 600:
            logger.error(f"Got HTTP {r.status_code} on {current_try} try for {url}. 🤨")
            sleep(backoff_time)
            backoff_time += backoff_factor
            current_try += 1
            continue
        else:
            logger.critical(
                f"Unexpected HTTP {r.status_code} on {current_try}. try for {url}. Skipping in panic! 😱"
            )
            raise cloudscraper.exceptions.CloudflareException
    else:
        logger.critical(
            f"Could not get {url} afer {current_try} tries. Skipping sadly. 😭"
        )
        raise cloudscraper.exceptions.CloudflareException

    # noinspection PyUnboundLocalVariable
    return r
