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
from .web.routing import Dispatcher, Routes, get, authenticate
import base64


class Restish(Routes, Dispatcher):
    def __init__(self, omni):
        super(Restish, self).__init__()
        self._omni = omni

    def any_realm(self, realm):
        return self._omni[realm]

    def admin_realm(self, realm):
        return self._omni["omni-admin"]

    @authenticate(any_realm)
    @get("{realm:dotid}/auth")
    def do_auth(self, request):
        request.response.content_type = "text/plain"
        return "OK\r\n"
