#!/usr/bin/env python
# -*- coding: utf-8 -*-

from urlparse import urljoin

import arrow
import requests
from bs4 import BeautifulSoup as bs
from trello.plugins.sync_to_trello import sync_to_trello


def parse_event(event, default_venue=None):
    over_21 = event.find(class_='over-21') is not None

    age_restriction = None
    if over_21:
        age_restriction = 21

    venue = default_venue
    has_venue = event.find(class_='location')
    if has_venue:
        venue = has_venue.text

    description = None
    has_description = event.find(class_='topline-info')
    if has_description:
        description = has_description.text

    ticket_link = None
    has_ticket_link = event.find(class_='ticket-link')
    if has_ticket_link:
        ticket_link = has_ticket_link.find('a').get('href')

    start_time = None
    has_start_time = event.select('.dtstart > .value-title')
    if has_start_time:
        start_time = arrow.get(has_start_time[0].get('title'))

    fobj = {
        'headliners': [x.text.split('SOLD OUT: ')[-1].split('at {}'.format(
            venue
        ))[0].strip() for x in event.find_all(class_='headliners')],
        'openers': [x.text for x in event.find_all(class_='supports')],
        'description': description,
        'age_restriction': age_restriction,
        'venue': venue,
        'ticket_link': ticket_link,
        'date': start_time,
        'tags': [],
    }

    return fobj


def main(trello, secrets):
    sites = [
        {
            'url': 'http://www.wonderballroom.com/all-shows/',
            'venue': 'Wonder Ballroom',
        },
    ]

    for site in sites:
        url = site['url']
        venue = site['venue']
        print("Scanning {}...".format(venue))
        content = requests.get(url)
        doc = bs(content.text, 'html.parser')
        events = doc.select('.vevent')
        event_urls = map(
            lambda x: (
                x,
                urljoin(site['url'], x.select('.url')[0].get('href'))
            ), events)

        final_events = []
        for event, url in event_urls:
            content = requests.get(url)
            doc = bs(content.text, 'html.parser')
            parsed_event = parse_event(doc, venue)
            final_events.append(parsed_event)
        sync_to_trello(trello, secrets, final_events)


def run(trello, secrets):
    main(trello, secrets)
