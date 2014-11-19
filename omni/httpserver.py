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

from webob.exc import HTTPNotFound
from .web import routing


class WSGIApplication(routing.Dispatcher):
    def __init__(self, omni):
        super(WSGIApplication, self).__init__()
        self._omni = omni
        self.add_route(self.do_auth)

    def any_realm(self, realm):
        try:
            return self._omni.get_realm_or_store(realm)
        except KeyError:
            raise HTTPNotFound()

    def admin_realm(self, realm):
        return self._omni["omni-admin"]

    @routing.get("/{realm:dotid}/authenticate")
    @routing.authenticate(any_realm)
    def do_auth(self, request):
        request.response.content_type = "text/plain"
        return "OK\r\n"

    __call__ = routing.Dispatcher.dispatch_wsgi
