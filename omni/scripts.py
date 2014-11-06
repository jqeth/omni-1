#! /usr/bin/env python
# -*- coding: utf-8 -*-
# vim:fenc=utf-8
#
# Copyright © 2014 Adrian Perez <aperez@igalia.com>
#
# Distributed under terms of the GPLv3 license.

"""
Defines the entry points for command line utilities.
"""

def omnid():
    from omni import app
    import sys
    import aiowsgi

    # Ugh. Trollius is used to implement asyncio in Python 2.x
    try:
        import asyncio
    except ImportError:
        import trollius as asyncio

    if "-h" in sys.argv or "--help" in sys.argv:
        raise SystemExit("Usage: omnid [path/to/omni.conf]")

    config = app.load_config(sys.argv[1]
            if len(sys.argv) == 2 else "/etc/omni.conf")
    application = app.make_wsgi_application(config)

    loop = asyncio.get_event_loop()
    args = aiowsgi.create_server(application, loop=loop,
            host=config["http"].get("host", "localhost"),
            port=config["http"].get("port", 8080))
    loop.run_forever()
