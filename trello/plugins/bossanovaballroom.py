#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function

import arrow
import requests
import json
from bs4 import BeautifulSoup as bs
from trello.plugins.sync_to_trello import sync_to_trello

ua = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_11_6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.36'


def clean_artists(artists):
    # throw away right side of any tour info
    artists = artists.split(u'–')[0]

    # throw away left side of "so and so presents: <artists>
    artists = artists.split(u'resents:')[-1]

    # replace other symbols to common separator
    for sym in ['&', 'plus ', 'featuring ', 'with ', 'w/']:
        artists = artists.replace(sym, ',')

    # split on ',', ditch 'guests'
    return [a.strip() for a in artists.split(',') if a.strip().lower() != 'guests']


def get_ticket(doc):
    ticket_link = None
    has_ticket_link = doc.find(class_='tribe-events-event-url')
    if has_ticket_link:
        ticket_link = has_ticket_link.find('a').get('href')
    else:
        sold_out = doc.find(class_='sold-out')
        if sold_out:
            ticket_link = "(Sold Out)"
    return ticket_link


def get_restriction(description):
    age_restriction = None
    if description is not None:
        if "21 and over" in description:
            age_restriction = 21
    return age_restriction


def get_rest(url):
    content = requests.get(url, headers={"User-Agent": ua})
    doc = bs(content.text, 'html.parser')
    ticket = get_ticket(doc)

    # Get the embedded json blob. Having things structured for us is a win!
    data = [x for x in doc.find_all('script')
            if x.get('type') == u'application/ld+json'][0].text
    jdata = json.loads(data)[0]

    date = arrow.get(jdata['startDate']).to('local')
    description = jdata['description']
    venue = jdata['location']['name']
    age_restriction = get_restriction(description)

    return (date, description, ticket, venue, age_restriction)


def parse_event(event, default_venue=None):
    primary_info = event.find(class_='fusion-tribe-primary-info')
    entry = primary_info.find(class_='url')

    artists = clean_artists(entry.text)

    headliners, openers = [artists[0]], artists[1:]

    (date, description, ticket_link, venue, age_restriction) = get_rest(entry['href'])

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

    sites = [
        {
            'url': 'http://bossanovaballroom.com/shows/list/?tribe_event_display=list&tribe_paged={}',
            'venue': 'Bossanova Ballroom',
        },
    ]

    for site in sites:
        url = site['url']
        venue = site['venue']
        print("Scanning {}... ".format(venue), end='')
        index = 1
        final_events = []
        # deal with pagination summary page
        while True:
            content = requests.get(url.format(index),
                                   headers={"User-Agent": ua})
            doc = bs(content.text, 'html.parser')

            events = doc.find_all(class_='type-tribe_events')

            if not events:
                break

            for event in events:
                parsed_event = parse_event(event, venue)
                final_events.append(parsed_event)

            index += 1

        print("Found {} items.".format(len(final_events)))
        sync_to_trello(trello, secrets, final_events)


def run(trello, secrets):
    main(trello, secrets)
