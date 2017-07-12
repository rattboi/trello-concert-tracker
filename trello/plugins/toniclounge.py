#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function

import re
import bs4
from bs4 import BeautifulSoup as bs
import arrow
import requests
from trello.plugins.sync_to_trello import sync_to_trello

sites = [
    {
        'url': 'http://www.tonicloungeportland.com/',
        'venue': 'Tonic Lounge',
    },
    {
        'url': 'http://highwatermarklounge.com/',
        'venue': 'High Water Mark Lounge',
    },
]


def parse_event(event, default_venue=None, artists=None, date=None):

    # There may be multiple of these. Get the first one.
    content = event.find(class_='grid-cell-box')

    age_restriction = 21

    venue = default_venue
    has_venue = content.find(class_='location')
    if has_venue:
        venue = has_venue.text

    description = None
    has_description = content.find(class_='EventSummary')
    if has_description:
        description = has_description.text

    ticket_link = None
    has_ticket_link = content.find(class_='btn-primary')
    if has_ticket_link:
        # The button is enclosed in the link tag, back up a step to grab it
        ticket_link = has_ticket_link.parent.get('href')

    # Just grope around for any time you can find...

    start_time = None
    has_start_time = re.search('(0?[1-9]|1[012])[APap][mM]', content.text)
    if has_start_time:
        start_time = arrow.get(has_start_time.group(0), 'hA')
        date = date.replace(hour=start_time.hour)

    (headliners, openers) = [artists[0]], artists[1:]

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


def get_date(elem):
    date_str = elem.text
    date = arrow.get(date_str, 'dddd MMMM D')
    now = arrow.now()
    year = now.year
    if now.month > date.month:
        year = year + 1
    return date.replace(year=year, tzinfo='local')


def get_artists(event):
    # artist always follows the date element
    content = event.find_next('p')
    # Remove any "xxx presents"-type header
    try:
        content.find('em').decompose()
    except AttributeError:
        pass
    # Remove any tags, keep the strings
    artists = [x.strip() for x in content.contents
               if not isinstance(x, bs4.element.Tag)]
    # Remove any "artist" over 30 characters. Probably not an artist at all
    artists = [x for x in artists if len(x) < 30]
    return artists


def main(site):
    url = site['url']
    venue = site['venue']
    content = requests.get(url)
    doc = bs(content.text, 'html.parser')
    events = doc.select('#grid')[0].select('a')
    # filter out any events that have no date (not real events)
    events = [e for e in events
              if len(e.find_all(class_='event-date')) > 0]

    final_events = []
    for event in events:
        # Get info from summary view
        date_elem = event.find(class_='event-date')
        date = get_date(date_elem)
        artists = get_artists(date_elem)

        # Get the rest from the specific event
        content = requests.get(event['href'])
        doc = bs(content.text, 'html.parser')
        parsed_event = parse_event(doc, venue, artists, date)

        # Fill in the fields we got from summary
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
