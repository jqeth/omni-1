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

from six import iteritems, string_types, text_type
from omni import store


def load_config(path):
    with open(path, "rb") as f:
        import wcfg
        return wcfg.load(f)


def make_application(config):
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

    return app


def make_wsgi_application(app_or_config):
    from omni import restish

    if not isinstance(app_or_config, store.OMNI):
        if isinstance(app_or_config, string_types + (text_type,)):
            app_or_config = load_config(app_or_config)
        app_or_config = make_application(app_or_config)

    assert isinstance(app_or_config, store.OMNI)
    return restish.Router(app_or_config)


class uWSGIApplication(object):
    def __call__(self, environ, start_response):
        import uwsgi
        config_file_path = uwsgi.opt["omni_config_file"]
        app = make_wsgi_application(config_file_path)
        # Replace the method itself, so make_wsgi_application()
        # is only called the first time, and the subsequent calls
        # go directly to the WSGI application itself.
        self.__call__ = app
        return self(environ, start_response)

uwsgi_application = uWSGIApplication()


