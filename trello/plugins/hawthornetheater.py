#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function

import arrow
import requests
from bs4 import BeautifulSoup as bs
from trello.plugins.sync_to_trello import sync_to_trello


def parse_headliners(artists):
    # separate each artist if multiple headliners
    artists = [x.strip() for x in artists[0].text.split('/')]

    # Remove tour postfix if it exists
    artists = [x.split(u'–')[0] for x in artists]

    return artists

def parse_openers(artists):
    # Remove With/with at beginning of text
    artists = artists[0].text
    artists = "".join(artists.split(u'with ', 1))
    artists = "".join(artists.split(u'With ', 1))

    # Remove last artist's 'and'
    artists = ','.join(artists.rsplit('and ', 1))

    # Split on commas
    artists = [x.strip() for x in artists.split(',') if x.strip() != '']

    return artists


def parse_event(event, default_venue=None):
    content = event.find(class_='tribe-events-single')

    show_notes = content.find(class_='rhino-event-notes')
    if show_notes is not None:
        over_21 = filter(lambda f: "photo ID" in f, show_notes.text.split('|'))

        age_restriction = None
        if over_21:
            age_restriction = 21

        venue = default_venue
        has_venue = event.find(class_='rhino-event-venue')
        if has_venue:
            venue = has_venue.text
    else:
        age_restriction = None
        venue = None

    description = None
    has_description = event.find(class_='tribe-events-single-event-description')
    if has_description:
        description = has_description.text

    ticket_link = None
    has_ticket_link = event.find(class_='on-sale')
    if has_ticket_link:
        ticket_link = has_ticket_link.find('a').get('href')
    else:
        sold_out = event.find(class_='sold-out')
        if sold_out:
            ticket_link = "(Sold Out)"

    date = None
    has_date = event.select('.rhino-event-date')
    if has_date:
        now = arrow.now()
        date = arrow.get(has_date[0].text, 'MMMM D')
        year = now.date().year
        if now.date().month > date.date().month:
            year = year + 1
        date = date.replace(year=year, tzinfo='local')

    start_time = None
    has_start_time = event.select('.rhino-event-time')
    if has_start_time:
        start_time = has_start_time[0].text.lower()
        ampm = start_time.split(' ')[-1]
        parts = start_time.split(' ')[0].split(':')
        hours = int(parts[0])
        mins = int(parts[1])
        if ampm.startswith('p'):
            hours += 12
        date = date.replace(hour=hours % 24, minute=mins % 60)

    headliners = []
    has_headliners = event.select(".rhino-event-header")
    if has_headliners:
        headliners = parse_headliners(has_headliners)

    openers = []
    has_openers = event.select(".rhino-event-subheader")
    if has_openers:
        openers = parse_openers(has_openers)

    print("Concert:")
    print("  Headliners:")
    for h in headliners:
        print(u"    {}".format(h))
    print("  Openers:")
    for o in openers:
        print(u"    {}".format(o))
    print("  Date: {}".format(date))
    print()

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


def main(trello, secrets):
    ua = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_11_6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.36'

    sites = [
        {
            'url': 'http://hawthornetheatre.com/events/',
            'venue': 'Hawthorne Theater',
        },
    ]

    for site in sites:
        url = site['url']
        venue = site['venue']
        print("Scanning {}... ".format(venue), end='')
        content = requests.get(url, headers={"User-Agent": ua})
        doc = bs(content.text, 'html.parser')
        events = doc.select('.rhino-event-header')
        event_urls = map(
            lambda x: (
                x,
                x.select('.url')[0].get('href')
            ), events)

        final_events = []
        for event, url in event_urls:
            content = requests.get(url, headers={"User-Agent": ua})
            doc = bs(content.text, 'html.parser')
            parsed_event = parse_event(doc, venue)
            final_events.append(parsed_event)
        print("Found {} items.".format(len(final_events)))
        sync_to_trello(trello, secrets, final_events)


def run(trello, secrets):
    main(trello, secrets)
