#!/usr/bin/env python
# -*- coding: utf-8 -*-

import time
import uuid
import json
import readline
import datetime
import pprint
from dateutil import tz

import arrow
import pylast

uuid_namespace = uuid.UUID(int=0x00)


def get_synced_items():
    try:
        f = open('synced_events.json', 'r+')
        contents = json.loads(f.read())
        f.close()
    except:
        contents = {
            'version': '1.0',
            'events': {},
        }
    return contents


def save_synced_items(contents):
    f = open('synced_events.json', 'w+')
    f.write(json.dumps(contents))
    f.close()


def human_format_list(items):
    if not items:
        return None
    formatted_list = [u', '.join(items[:-1])]
    formatted_list.append(items[-1])
    formatted_list = u' and '.join(x for x in formatted_list if x)
    return formatted_list


def trello_format_list(items):
    return u'\n'.join(u'- {}'.format(x) for x in items)


def get_play_count(lfm, artist):
    try:
        f = open('lastfm_cache.json', 'r+')
        contents = json.loads(f.read())
        f.close()
    except:
        contents = {
            'artists': {},
        }

    if artist in contents['artists'].keys():
        count = contents['artists'][artist]['play_count']
    else:
        a = lfm.get_artist(artist)
        a.username = lfm.username
        try:
            count = a.get_userplaycount()
        except pylast.WSError:
            count = 0
        contents['artists'][artist] = {
            'play_count': count,
            'updated': arrow.utcnow().isoformat(),
            'similar_artists': None,
        }
        time.sleep(0.3)

    f = open('lastfm_cache.json', 'w+')
    f.write(json.dumps(contents))
    f.close()

    return count


def get_similar_artists(lfm, artist):
    f = open('lastfm_cache.json', 'r+')
    contents = json.loads(f.read())
    f.close()

    if contents['artists'][artist]['similar_artists'] is None:
        try:
            a = lfm.get_artist(artist)
            similar = a.get_similar()
        except pylast.WSError:
            similar = []
        similar_artists = {}
        for art in similar:
            similar_artists[art.item.name] = {
                'match': art.match,
            }
        contents['artists'][artist]['similar_artists'] = similar_artists
        time.sleep(0.3)
    else:
        similar_artists = contents['artists'][artist]['similar_artists']

    f = open('lastfm_cache.json', 'w+')
    f.write(json.dumps(contents))
    f.close()
    return similar_artists


def set_due_date(card, date):
    card._conn.put(u"{}/due".format(card._path), params={'value': date.isoformat()})


def sync_to_trello(trello, secrets, song_objects, force_add=None):

    pw_hash = secrets['lastfm'].get('password_hash')
    if pw_hash is None:
        pw_hash = pylast.md5(secrets['lastfm']['password'])

    lfm = pylast.LastFMNetwork(
        api_key=secrets['lastfm']['api_key'],
        api_secret=secrets['lastfm']['secret'],
        username=secrets['lastfm']['username'],
        password_hash=pw_hash,
    )

    concerts_board = [x for x in trello.me.boards if x.name == 'Concerts'][0]
    landing_list = [x for x in concerts_board.lists if x.name == 'Coming to Town'][0]

    archive_cards = [x for x in landing_list.cards if arrow.get(x.badges['due']) < arrow.utcnow()]
    for card in archive_cards:
        card.close()

    added_cards = [x for x in concerts_board.cards if '*UUID: ' in x.desc]
    existing_uuids = []
    for card in added_cards:
        uuid_line = [x for x in card.desc.split('\n') if '*UUID: ' in x][0]
        existing_uuids.append(uuid_line.split('*UUID: ')[-1].split('*')[0])

    for obj in song_objects:
        uuid_string = u"{} playing at {} on {}".format(
            obj['headliners'],
            obj['venue'],
            obj['date'].strftime('%X'),
        )
        obj['uuid'] = uuid.uuid5(uuid_namespace, uuid_string).hex
    contents = get_synced_items()

    existing_uuids += contents['events'].keys()

    new_shows = [x for x in song_objects if x['uuid'] not in existing_uuids]
    if new_shows:
        print("Adding {} shows to trello".format(len(new_shows)))
    for show in new_shows:
        show['_internal'] = {}
        show['play_counts'] = {}
        show['_internal']['title'] = u"{} at {}".format(
            human_format_list(show['headliners']),
            show['venue'],
        )

        description = []

        if show['ticket_link']:
            description = [
                u"[Click here to purchase tickets]({})".format(show['ticket_link']),
                "*Ticket Delivery Method*:",
                "",
            ]

        if show['age_restriction']:
            description += [
                "**{}+ Event**".format(show['age_restriction']),
                "",
            ]

        if show['headliners']:
            description += [
                u"Headliners:",
                u"-----------",
                trello_format_list(show['headliners']),
                "",
            ]

        if show['openers']:
            description += [
                u"Opening Acts:",
                u"-------------",
                trello_format_list(show['openers']),
                "",
            ]

        if show['description']:
            description += [
                show['description'],
                "",
            ]

        description += [
            u"Venue: {}".format(show['venue']),
            u"",
            u"Date: {}".format(show['date'].isoformat()),
        ]
        description += [u"*UUID: {}*".format(show['uuid'])]

        show['_internal']['description'] = u"\n".join(description)

        all_artists = show['headliners'] + show['openers']

        show_play_count = 0
        for artist in all_artists:
            count = get_play_count(lfm, artist)
            show['play_counts'][artist] = count
            show_play_count = max(count, show_play_count)

        add_card = False
        if force_add:
            add_card = True

        labels = []
        if show_play_count < 10:
            labels.append('green')
        elif show_play_count < 100:
            labels.append('yellow')
            add_card = True
        elif show_play_count < 500:
            labels.append('orange')
            add_card = True
        else:
            labels.append('red')
            add_card = True

        comments = []

        print("  Syncing: {}".format(all_artists))
        if show_play_count < 100:
            print("    less than 100 plays")
            for artist in all_artists:
                similar_artists = get_similar_artists(lfm, artist)
                print("    similar artists: {}".format(",".join(similar_artists)))
                max_count = 0
                matches = []
                for art in [k for k, v in similar_artists.items() if v['match'] >= .75]:
                    count = get_play_count(lfm, art)
                    print("      count for similar artist {}: {}".format(art, count))
                    if count >= 10:
                        matches.append(u"{} ({} plays)".format(art, count))
                        max_count = max(count, max_count)

                if matches:
                    add_card = True
                    comment = [
                        u"{} is similar to other bands you listen to:".format(artist),
                        u"-------------------------------------",
                        trello_format_list(matches),
                    ]
                    comments.append(u'\n'.join(comment))
                    if max_count >= 50:
                        labels.append('sky')

        elif show_play_count < 500:
            labels.append('sky')
        else:
            labels.append('pink')

        if add_card:
            print(u"{} on {}".format(
                show['_internal']['title'],
                show['date'],
            ))
            card = landing_list.add_card(
                show['_internal']['title'],
                show['_internal']['description']
            )
            set_due_date(card, show['date'])
            for label in list(set(labels)):
                if label not in card._valid_label_colors:
                    card._valid_label_colors.append(label)
                card.set_label(label)

            for comment in comments:
                card.add_comment(comment)

        show.pop('_internal')
        contents['events'][show['uuid']] = show
        contents['events'][show['uuid']]['date'] = show['date'].isoformat()
        if add_card:
            time.sleep(0.3)

        save_synced_items(contents)


def add(trello, secrets):
    contents = get_synced_items()
    venues = list(set(map(lambda x: x[1]['venue'], contents['events'].items())))
    bands = []
    for k, event in contents['events'].items():
        bands += event['headliners']
        bands += event['openers']

    f = open('lastfm_cache.json', 'r+')
    lfm_cache = json.loads(f.read())
    f.close()
    bands += lfm_cache['artists'].keys()

    def completer_factory(options):
        def completer(text, state):
            items = list(set(filter(lambda x: x.lower().startswith(text.lower()), options)))
            if not items:
                items = list(set(filter(lambda x: text.lower() in x.lower(), options)))

            if state < len(items):
                return items[state]
            else:
                return None
        return completer

    def request_item(item, tp, completions=None, default=None):
        if default is None and tp in [list]:
            default = tp()
        if not completions:
            completions = []
        readline.parse_and_bind("tab: complete")
        readline.set_completer(completer_factory(completions))
        readline.set_completer_delims('')
        final_value = None
        if default:
            value = input("{} (Default: {}): ".format(item, default))
        else:
            value = input("{}: ".format(item))
        if value:
            if tp in [list]:
                final_value = []
                while value:
                    final_value.append(value)
                    value = input("{} (more): ".format(item))
            elif tp is datetime.datetime:
                for splitter in ['/', '-', ' ']:
                    if len(value.split(splitter)) == 3:
                        mo, da, yr = value.split(splitter)
                        if all([mo.isdigit(), da.isdigit(), yr.isdigit()]):
                            final_value = arrow.get(int(yr), int(mo), int(da))
                            break
                else:
                    final_value = arrow.get(value)
                final_value = final_value.replace(tzinfo=tz.tzlocal())
            else:
                final_value = tp(value)
        if not final_value:
            final_value = default
        return final_value

    events = []
    event = {}
    continue_interview = True
    while continue_interview:
        print('========================================')
        event = {
            'date': request_item('Date', datetime.datetime, default=event.get('date')),
            'headliners': request_item('Headliners', list, bands, default=event.get('headliners')),
            'openers': request_item('Openers', list, bands, default=event.get('openers')),
            'venue': request_item('Venue', str, venues, default=event.get('venue')),
            'description': request_item('Description', str, default=event.get('description')),
            'age_restriction': request_item('Age Restrictions (Int)', int, [18, 21], default=event.get('age_restriction')),
            'ticket_link': request_item('Ticket Purchase Link', str, default=event.get('ticket_link')),
            'tags': [],
        }
        print('----------------------------------------')
        pprint.pprint(event)
        if input("Confirm event [Y/n]").lower() == 'n':
            print("Press enter to keep the default value. Otherwise provide your changes.")
            continue
        events.append(event)
        event = {}
        print('')
        continue_interview = input("Add another event? [Y/n]").lower() != 'n'

    sync_to_trello(trello, secrets, events, force_add=True)


def review(trello, secrets):
    print("In reviewing mode...")
    contents = get_synced_items()
    import pprint
    pprint.pprint(contents)
    pass
