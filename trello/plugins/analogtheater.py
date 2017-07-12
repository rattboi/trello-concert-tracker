#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function

import re
import json
import arrow
import requests
from trello.plugins.sync_to_trello import sync_to_trello

sites = [
    {
        'url': 'https://www.eventbrite.com/venue/api/feeds/organization/92.json',
        'venue': "Analog Theater",
    },
]


def clean_artists(artists):
    final_artists = []
    for artist in artists:
        artist = re.sub(r'\([^)]*\)', '', artist)
        for sym in ['w/', '/', '&', 'featuring']:
            artist = artist.replace(sym, ',')
        artist = ','.join(artist.rsplit(' and ', 1))
        artist = artist.split(',')
        artist = [x.strip() for x in artist]
        artist = [x for x in artist
                  if (x.lower() != u'guests') and (x)]
        final_artists.extend(artist)

    return final_artists


def parse_event(event):
    artists = event['performing']
    if not artists:
        artists = [event['title']]

    artists = clean_artists(artists)
    headliners, openers = [artists[0]], artists[1:]

    age_restriction = None
    if u"ALL AGES" not in event['restrictions']:
        age_restriction = 21

    venue = event['venue_name']
    ticket_link = "https://www.eventbrite.com/e/{}".format(event['eventbrite_id'])

    description = None
    if event.get('description'):
        description = event['description']

    date_str = event['starts_at']
    time_str = event['doors_at']
    date = arrow.get("{} {}".format(date_str, time_str),
                     "YYYY-MM-DD HH:mm").replace(tzinfo='local')

    fobj = {
        'headliners': headliners,
        'openers': openers,
        'description': description,
        'age_restriction': age_restriction,
        'venue': venue,
        'ticket_link': ticket_link,
        'date': date,
        'tags': [],
    }

    return fobj


def main(site):
    url = site['url']
    venue = site['venue']
    content = requests.get(url)
    events = json.loads(content.text)

    final_events = []
    for event in events:
        parsed_event = parse_event(event)
        final_events.append(parsed_event)
    return final_events


def run(trello, secrets):
    final_events = []
    for site in sites:
        print("Scanning {}... ".format(site['venue']), end='')
        events = main(site)
        print("Found {} items.".format(len(events)))
        final_events.extend(events)
    sync_to_trello(trello, secrets, final_events)
    return [True]


def tester(site):
    events = main(site)
    if len(events) == 0:
        print("ERROR: No results for {}".format(site['venue']))
        return False
    else:
        return True


def test(trello, secrets):
    return [tester(site) for site in sites]
