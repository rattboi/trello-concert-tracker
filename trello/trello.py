#!/usr/bin/env python
# -*- coding: utf-8 -*-

import glob
import sys
import os
import imp

from trollop.lib import TrelloConnection

import secret

import warnings
warnings.filterwarnings("ignore")


def cli():
    argvs = sys.argv[1:]
    action = argvs[0]
    trello = TrelloConnection(
        secret.key['trello']['api_key'],
        secret.key['trello']['token'])

    results = []
    plugins = [x
               for x in glob.glob('trello/plugins/*.py')
               if '__init__' not in x]
    for plugin in plugins:
        plugin_ext = os.path.splitext(plugin)[1]
        plugin_filename = os.path.basename(plugin).split(plugin_ext)[0]
        plug = imp.load_source('plugins.{}'.format(plugin_filename), plugin)
        if hasattr(plug, action):
            method = getattr(plug, action)
            if callable(method):
                result = method(trello, secret.key)
                results.extend(result)
    if not all(results):
        sys.exit(1)

if __name__ == '__main__':
    cli()
