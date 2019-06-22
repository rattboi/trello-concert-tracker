#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function

import arrow
import requests
from bs4 import BeautifulSoup as bs
from trello.plugins.sync_to_trello import sync_to_trello


def get_restriction(doc):
    age_restriction_content = doc.find(class_='age-restriction').text
    age_restriction = None
    if age_restriction_content is not None:
        if "and over" in age_restriction_content:
            age_restriction = 21
    return age_restriction


def get_ticket(doc):
    ticket_link = None
    has_ticket_link = doc.find(class_='buy-tickets-link')
    if has_ticket_link:
        ticket_link = has_ticket_link.find('a').get('href')
    else:
        sold_out = doc.find(class_='sold-out')
        if sold_out:
            ticket_link = "(Sold Out)"
    if not ticket_link:
        ticket_link = "(No Ticket)"
    return ticket_link


def parse_headliner(h):
    h = h.replace('Featuring', '')
    h = h.replace('featuring', '')
    h = h.split(',')
    h = [a.strip() for a in h]
    return h


def parse_headliners(doc):
    headliner_content = doc.find_all(class_='headliner')
    headliners = [h.text for h in headliner_content]
    headliners = [parse_headliner(h) for h in headliners]
    headliners = [y for x in headliners for y in x]
    return headliners


def parse_opener(opener):
    opener = "".join(opener.split(u'with ', 1))
    opener = "".join(opener.split(u'With ', 1))
    opener = "".join(opener.split(u'w/', 1))
    opener = ','.join(opener.rsplit('and ', 1))

    # Split on commas
    openers = [x.strip() for x in opener.split(',') if x.strip() != '']
    return openers


def parse_openers(doc):
    opener_content = doc.find_all(class_='supports')
    openers = [o.text for o in opener_content]
    openers = [parse_opener(o) for o in openers]
    openers = [y for x in openers for y in x]
    return openers


def parse_event(event, venue):
    url = event['value']
    content = requests.get('http://www.crystalballroompdx.com{}'.format(url))
    doc = bs(content.text, 'html.parser')
    event_content = doc.find(class_='event')

    if event_content is None:
        return None

    headliners = parse_headliners(event_content)

    openers = parse_openers(event_content)

    description_content = event_content.find(class_='supports-bios')
    description = description_content.text

    age_restriction = get_restriction(event_content)

    ticket_link = get_ticket(event_content)

    date = None
    has_date = event_content.select('.dates')
    if has_date:
        now = arrow.now()
        date = arrow.get(has_date[0].text, 'dddd, MMMM D')
        year = now.date().year
        date = date.replace(year=year, tzinfo='local')
        if date < now:
            year = year + 1
        date = date.replace(year=year, tzinfo='local')

    has_start_time = event_content.select('.times')
    if has_start_time:
        time = has_start_time[0].text
        show_time = [a for a in time.lower().split(',') if 'show' in a]
        if len(show_time) == 1:
            show_time = show_time[0]
            show_time = show_time.replace('show', '').strip()

            ampm = show_time.split(' ')[-1]
            parts = show_time.split(' ')[0].split(':')
            try:
                hours = int(parts[0])
            except:
                hours = int(''.join(filter(lambda x: x.isdigit(), parts[0])))
            if len(parts) > 1:
                mins = int(parts[1])
            else:
                mins = 0
            if ampm.startswith('p'):
                hours += 12
            date = date.replace(hour=hours % 24, minute=mins % 60)

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
            'url': "http://www.crystalballroompdx.com/events/search/Any?joint_name=Crystal+Ballroom&location_id=2",
            'venue': "Crystal Ballroom",
        },
    ]

    for site in sites:
        url = site['url']
        venue = site['venue']
        print("Scanning {}... ".format(venue), end='')
        headers = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.12; rv:57.0) Gecko/20100101 Firefox/57.0',
                   'X-Requested-With': 'XMLHttpRequest',
                   'Host': 'www.crystalballroompdx.com',
                   'Referer': 'http://www.crystalballroompdx.com/1904-cbr-event-calendar',
                   'Accept': 'application/json, text/javascript, */*; q=0.01',
                   'Accept-Language': 'en-US,en;q=0.5'}
        content = requests.get(url, headers=headers)
        events = content.json()

        final_events = [parse_event(event, venue) for event in events 
                        if parse_event(event, venue) is not None]
        print("Found {} items.".format(len(final_events)))
        [print("  {}".format(",".join(event['headliners']))) for event in final_events]
        sync_to_trello(trello, secrets, final_events)


def run(trello, secrets):
    main(trello, secrets)
