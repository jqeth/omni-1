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
from . import store, valid


config_realms_schema = valid.Schema({
    "methods": [valid.DotIdentifier],
    valid.Optional("description"): valid.Text,
})


def load_config(path):
    with open(path, "rb") as f:
        import wcfg
        return wcfg.load(f)


def make_application(omni_config):
    app = store.OMNI()
    for name, store_config in iteritems(omni_config.get("stores", {})):
        store_type = name.split(".", 1)[0]
        store_module = store.find(store_type)
        try:
            store_config = store_module.config_schema.validate(store_config)
        except valid.SchemaError as e:
            raise valid.SchemaError((), "in 'stores' section, item '{}': {!s}"
                    .format(name, e))
        app.add_store(name, store_module.from_config(store_config))

    for name, realm_config in iteritems(omni_config.get("realms", {})):
        try:
            realm_config = config_realms_schema.validate(realm_config)
        except valid.SchemaError as e:
            raise valid.SchemaError((), "in 'realms' section: {!s}"
                    .format(e))

        methods = realm_config["methods"]
        try:
            realm = store.Realm(realm_config.get("description", name),
                    (app.get_store(name) for name in methods))
        except KeyError as e:
            raise valid.SchemaError((), ("in 'realms' section, item '{s}':"
                " undefined store '{!s}'").format(name, e))
        app.add_realm(name, realm)

    return app


def make_wsgi_application(app_or_config):
    from omni.httpserver import WSGIApplication

    if not isinstance(app_or_config, store.OMNI):
        if isinstance(app_or_config, string_types + (text_type,)):
            app_or_config = load_config(app_or_config)
        app_or_config = make_application(app_or_config)

    assert isinstance(app_or_config, store.OMNI)
    return WSGIApplication(app_or_config)


class uWSGIApplication(object):
    def __call__(self, environ, start_response):
        import uwsgi
        config_file_path = uwsgi.opt["omni_config_file"]
        app = make_wsgi_application(load_config(config_file_path))
        # Replace the method itself, so make_wsgi_application()
        # is only called the first time, and the subsequent calls
        # go directly to the WSGI application itself.
        self.__call__ = app
        return app(environ, start_response)

uwsgi_application = uWSGIApplication()


