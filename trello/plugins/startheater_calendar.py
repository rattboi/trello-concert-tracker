#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function

import arrow

import requests
from bs4 import BeautifulSoup as bs
from trello.plugins.sync_to_trello import sync_to_trello

#import sys
#from PyQt4.QtGui import QApplication
#from PyQt4.QtCore import QUrl
#from PyQt4.QtWebKit import QWebPage
#
#class Render(QWebPage):
#    def __init__(self, url):
#        self.app = QApplication(sys.argv)
#        QWebPage.__init__(self)
#        self.loadFinished.connect(self._loadFinished)
#        self.mainFrame().load(QUrl(url))
#        self.app.exec_()
#
#    def _loadFinished(self, result):
#        self.frame = self.mainFrame()
#        self.app.quit()


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

    fobj = {
        'headliners': [x.text.split('SOLD OUT: ')[-1].split('at {}'.format(
            venue
        ))[0].strip() for x in event.find_all(class_='headliners')],
        'openers': [x.text for x in event.find_all(class_='supports')],
        'description': description,
        'age_restriction': age_restriction,
        'venue': venue,
        'ticket_link': ticket_link,
        'tags': [],
    }

    return fobj


def main(trello, secrets):
    sites = [
        {
            'url': 'http://startheaterportland.com/',
            'venue': 'Star Theater',
        },
    ]

    for site in sites:
        url = site['url']
        venue = site['venue']
        print("Scanning {}... ".format(venue), end='')
        result = Render(url)

        import pdb; pdb.set_trace()
        return

        content = requests.get(url)
        doc = bs(content.text, 'html.parser')
        days = doc.select('.tw-section')

        import pdb; pdb.set_trace()

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
        print("Found {} items.".format(len(final_events)))
        [print("  {}".format(",".join(event['headliners']))) for event in final_events]
        sync_to_trello(trello, secrets, final_events)


def test(trello, secrets):
    main(trello, secrets)
