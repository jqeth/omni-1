#! /usr/bin/env python
# -*- coding: utf-8 -*-
# vim:fenc=utf-8
#
# Copyright © 2014 Adrian Perez <aperez@igalia.com>
#
# Distributed under terms of the GPLv3 license.

"""
Command line entry point for the OMNI daemon.
"""

import omni.store
import omni.auth
import wcfg


class OMNI(object):
    def __init__(self):
        self._stores = {}
        self._realms = {}

    def add_store(self, name, store):
        if name in self._stores:
            raise KeyError("Store {} is already present".format(name))
        assert isinstance(store, omni.store.Base)
        self._stores[name] = store

    def add_realm(self, name, realm):
        if name in self._realms:
            raise KeyError("Realm {} is already present".format(name))
        # TODO: assert isinstance(realm, omni.auth.Realm)
        self._realms[name] = realm

    def run(self):
        pass


def main():
    import sys
    from six import iteritems

    with open(sys.argv[1], "rb") as f:
        config = wcfg.load(f)

    app = OMNI()
    for name, store_config in iteritems(config.get("stores", {})):
        store_type = name.split(".", 1)[0]
        store = omni.store.find(store_type).from_config(store_config)
        app.add_store(name, store)

if __name__ == "__main__":
    main()
