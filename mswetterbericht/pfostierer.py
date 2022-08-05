import json
import sys
import datetime
import re

from argparse import ArgumentParser, Namespace

import praw
import praw.models
from mswetterbericht import wetterbericht

user_agent = "User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:103.0) Gecko/20100101 Firefox/103.0"
subreddit_name = "carbonarastrasse"
bot_add_line = "\n\n*^^Dieser ^^Wetterbericht ^^wurde ^^automatisiert ^^erstellt ^^und ^^ist ^^ohne ^^Unterschrift " \
               "^^gültig.*"
# subreddit_name = "mauerstrassenwetten"


def parse_args() -> Namespace:
    parser = ArgumentParser()
    parser.add_argument('--credentials-file', required=True)
    args = parser.parse_args()

    return args


def find_ddt(reddit: praw.Reddit) -> praw.models.Submission:
    # Format the search Regex for the Daily Discussion Thread
    ddt_date = datetime.date.today().strftime('%B %d, %Y')
    msw = reddit.subreddit(subreddit_name)

    for submission in msw.hot(limit=3):
        print(submission.title)
        # Ignore unstickied posts directly in case
        # there's a shitpost with the same date format
        if not submission.stickied:
            continue

        if re.search(ddt_date, submission.title):
            return submission


args = parse_args()

try:
    with open(args.credentials_file) as f:
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


ddt = find_ddt(reddit)
ddt.reply(body=wetterbericht.wetterbericht() + bot_add_line)
