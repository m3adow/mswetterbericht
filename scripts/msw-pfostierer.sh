#!/bin/bash
set -x

############################################################################
# This script is intended to be run as Cronjob for daily forecast creation #
############################################################################

# Directory where the mswetterbericht repo is located
CWD="${CWD:-${HOME}/src/mswetterbericht}"
# Comment this out for testing
SUBREDDIT="${SUBREDDIT:-carbonarastrasse}"

run_mswetterbericht() {
  poetry run python mswetterbericht/pfostierer.py \
    --credentials-file "secret/praw-credentials.json" \
    --instruments-file "files/instruments.yaml" \
    --prose-file "files/prose.yaml" \
    --subreddit "${SUBREDDIT}" \
  || return 1
}

cd "${CWD}" || exit 1
# Make sure the branch is up2date (kind of an "Auto Updater")
git pull

# Try to update poetry modules when the normal wetterbericht fails
if ! run_mswetterbericht
then
  poetry update
  run_mswetterbericht \
    || exit 1
  # Reset branch afterwards to preserve auto-update via "git pull"
  git checkout --hard HEAD
fi
