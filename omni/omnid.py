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
from omni import restish
from wsgiref.simple_server import make_server
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
        realm = store.Realm(str(realm_config.get("description", name)),
                (app.get_store(name) for name in methods))
        app.add_realm(name, realm)
        print("Realm {} registered:".format(name), realm)

    wsgi_app = make_server("localhost", 8080, restish.Router(app))
    wsgi_app.serve_forever()


if __name__ == "__main__":
    main()
