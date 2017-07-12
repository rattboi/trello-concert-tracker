#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function

import arrow

import requests
from bs4 import BeautifulSoup as bs
from trello.plugins.sync_to_trello import sync_to_trello

sites = [
    {
        'url': 'http://www.mississippistudios.com/calendar',
        'venue': 'Mississippi Studios',
    },
    {
        'url': 'http://www.dougfirlounge.com/calendar',
        'venue': 'Doug Fir Lounge',
    },
    {
        'url': 'http://www.revolutionhall.com/calendar',
        'venue': 'Revolution Hall',
    },
    {
        'url': 'http://www.aladdin-theater.com/calendar',
        'venue': 'Aladdin Theater',
    },
    {
        'url': 'http://www.holocene.org/calendar',
        'venue': 'Holocene',
    },
]

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

    headliners = event.find_all(class_='headliners')
    headliners = [x.text.split('SOLD OUT: ')[-1].split(
                    'at {}'.format(venue)
                  )[0].strip()
                  for x in headliners]
    headliners = [x.split('/') for x in headliners]
    headliners = [item.strip() for sublist in headliners for item in sublist]


    openers = [x.text for x in event.find_all(class_='supports')]

    fobj = {
        'headliners': headliners,
        'openers': openers,
        'description': description,
        'age_restriction': age_restriction,
        'venue': venue,
        'ticket_link': ticket_link,
        'tags': [],
    }

    return fobj


def main(site):
    url = site['url']
    venue = site['venue']
    content = requests.get(url)
    doc = bs(content.text, 'html.parser')
    days = doc.select('.vevent.data')
    final_events = []
    for day in days:
        time_str = day.find('span').get('title')
        date = arrow.get(time_str)
        events = day.find_all('div', class_='one-event')
        for event in events:
            parsed_event = parse_event(event, venue)
            start_time = event.find(class_='start-time')
            if start_time:
                start_time = start_time.text.lower()
                ampm = start_time.split(' ')[-1]
                parts = start_time.split(' ')[0].split(':')
                hours = int(parts[0])
                mins = int(parts[1])
                if ampm.startswith('p'):
                    hours += 12
                date = date.replace(hour=hours % 24, minute=mins % 60)
            parsed_event['date'] = date
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
