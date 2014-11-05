#! /usr/bin/env python
# -*- coding: utf-8 -*-
# vim:fenc=utf-8
#
# Copyright © 2014 Adrian Perez <aperez@igalia.com>
#
# Distributed under terms of the GPLv3 license.

"""
Exposes a REST-ish authentication interface to OMNI.
"""

from webob.exc import HTTPNotFound, HTTPUnauthorized
from webob.dec import wsgify


class Router(object):
    def __init__(self, omni):
        self._omni = omni

    def do_auth(self, request, realm):
        print("do_auth OK", realm)
        request.response.content_type = "text/plain"
        request.response.write("OK")

    @wsgify
    def __call__(self, request):
        realm = request.path_info_pop()
        if realm not in self._omni:
            raise HTTPNotFound()

        realm = self._omni[realm]
        requires_authentication = False
        action = request.path_info_pop()

        if action.startswith("+"):
            requires_authentication = True
            action = action[1:]

        method = getattr(self, "do_" + action, None)
        if method is None:
            raise HTTPNotFound()

        if getattr(method, "public", False):
            requires_authentication = False

        if requires_authentication:
            # Requires being already authenticated.
            username, password = request.authorization or (None, None)
            if username is None or not realm.authenticate(username, password):
                raise HTTPUnauthorized(headers=[
                    ("WWW-Authenticate",
                        "Basic realm=\"{}\"".format(realm.description))])

        return method(request, realm)

