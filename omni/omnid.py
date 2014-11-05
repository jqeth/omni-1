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

from omni import store
import wcfg


def main():
    import sys
    from six import iteritems

    with open(sys.argv[1], "rb") as f:
        config = wcfg.load(f)

    app = store.OMNI()
    for name, store_config in iteritems(config.get("stores", {})):
        store_type = name.split(".", 1)[0]
        store_item = store.find(store_type).from_config(store_config)
        app.add_store(name, store_item)
        print("Store {} registered (type: {}), config:".format(name,
            store_type), store_config)

    for name, realm_config in iteritems(config.get("realms", {})):
        methods = realm_config["methods"]
        realm = store.Realm((app.get_store(name) for name in methods))
        app.add_realm(name, realm)
        print("Realm {} registered:".format(name), realm)

if __name__ == "__main__":
    main()
