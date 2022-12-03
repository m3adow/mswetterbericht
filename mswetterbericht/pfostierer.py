import json
import datetime
import re

from argparse import ArgumentParser, Namespace

import praw.models
from wetterbericht import forecast

user_agent = "User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:103.0) Gecko/20100101 Firefox/103.0"
# subreddit = "mauerstrassenwetten"
bot_add_line = (
    "\n\n*^^Dieser ^^Wetterbericht [^^wurde ^^automatisiert ^^erstellt]"
    "(https://github.com/m3adow/mswetterbericht) ^^und ^^ist ^^ohne ^^Unterschrift ^^gültig.*"
)
subreddit = "carbonarastrasse"


def parse_args() -> Namespace:
    parser = ArgumentParser()
    parser.add_argument("--prose-file", required=True)
    parser.add_argument("--instruments-file", required=True)
    parser.add_argument("--credentials-file", required=True)
    parser.add_argument("--subreddit", default=subreddit)
    args = parser.parse_args()

    return args


def find_ddt(reddit: praw.Reddit, target_sub: str) -> praw.models.Submission:
    # Format the search Regex for the Daily Discussion Thread
    ddt_date = datetime.date.today().strftime("%B %d, %Y")
    msw = reddit.subreddit(target_sub)

    for submission in msw.hot(limit=3):
        # Ignore unstickied posts directly in case
        # there's a shitpost with the same date format
        if not submission.stickied:
            continue

        if re.search(ddt_date, submission.title):
            return submission
    else:
        print("Could not find Daily Discussion Thread. 💩 Exiting.")
        exit(1)


args = parse_args()

try:
    with open(args.credentials_file) as f:
        # TODO: Maybe implement JSONschma
        """
        Required JSON structure:
        {
            "client_id": "xxxxxx",
            "client_secret": "xxxxxx",
            "username": "carbonara-yolo",
            "password": "xxxxxx"
        }
        """
        creds = json.load(f)
except (IndexError, FileNotFoundError) as e:
    print("Could not load PRAW credentials file: %s" % e)
    exit(1)

reddit = praw.Reddit(**creds, check_for_updates=False, user_agent=user_agent)

ddt = find_ddt(reddit, target_sub=args.subreddit)
ddt.reply(
    body=forecast(instruments_file=args.instruments_file, prose_file=args.prose_file)
    + bot_add_line
)
