#!/usr/bin/env python
from setuptools import setup

setup(
    name="Trello Integrations",
    version="0.1.0",
    author="Britt Gresham",
    author_email="britt@brittg.com",
    description=("Integrate various scripts into trello"),
    license="MIT",
    install_requires=[
        'requests',
        'beautifulsoup4',
        'pylast',
        'arrow',
    ],
    entry_points="""\
    [console_scripts]
    sync_trello = trello.trello:cli
    """,
)
