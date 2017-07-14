#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function

import arrow
import requests
from bs4 import BeautifulSoup as bs
from trello.plugins.sync_to_trello import sync_to_trello
from dateutil import tz


def parse_event(event, default_venue=None):

    basic_info = event.select('.tw-plugin-basic-event-info')[0]

    age_restriction = 21
    venue = default_venue

    ticket_link = None
    has_ticket_link = basic_info.find(class_='tw_onsale')
    if not has_ticket_link:
        has_ticket_link = basic_info.find(class_='tw_ticketssold')
    if has_ticket_link:
        ticket_link = has_ticket_link.get('href')

    attractions = []
    has_attractions = basic_info.find(class_='tw-attraction-list')
    if not has_attractions:
        return
    attraction_list = has_attractions.find_all('li')
    attractions = [a.text.strip() for a in attraction_list]
    headliners, openers = [attractions[0]], attractions[1:]

    start_time = None
    has_start_time = basic_info.select('.tw-event-date-time')
    if has_start_time:
        date_str = has_start_time[0].select('.tw-event-date')[0].text
        time_str = has_start_time[0].select('.tw-event-time')[0].text
        full_str = "{} {}".format(date_str, time_str)
        start_time = arrow.get(
            full_str, "MMMM D, YYYY h:mm a"
        ).replace(tzinfo=tz.tzlocal())

    description = None
    has_description = event.find(class_='topline-info')
    if has_description:
        description = has_description.text

    fobj = {
        'headliners': headliners,
        'openers': openers,
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
            'url': "http://danteslive.com/event/?twpage={}",
            'venue': "Dante's",
        },
    ]

    for site in sites:
        url = site['url']
        venue = site['venue']
        print("Scanning {}... ".format(venue), end='')
        index = 0
        final_events = []
        # deal with pagination of events summary page
        while True:
            content = requests.get(url.format(index))
            doc = bs(content.text, 'html.parser')
            event_list = doc.select('.tw-plugin-upcoming-event-list')[0]
            events = event_list.find_all('td', style=False)

            # It returns a page for any index. If no events, we've reached the
            # last page
            if not events:
                break

            event_links = [event.find('a')['href'] for event in events]
            # dive into each event, as the info is much more regular in the
            # event page vs the summary page
            for link in event_links:
                event_content = requests.get(link)
                event = bs(event_content.text, 'html.parser')
                parsed_event = parse_event(event, venue)
                final_events.append(parsed_event)
            index += 1
        print("Found {} items.".format(len(final_events)))
        sync_to_trello(trello, secrets, final_events)


def run(trello, secrets):
    main(trello, secrets)
