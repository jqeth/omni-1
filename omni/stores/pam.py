#! /usr/bin/env python
# -*- coding: utf-8 -*-
# vim:fenc=utf-8
#
# Copyright © 2014 Adrian Perez <aperez@igalia.com>
#
# Distributed under terms of the GPLv3 license.

"""
Authenticate users using PAM.

Uses PAM (via the `simplepam <https://pypi.python.org/pypi/simplepam/>`_
module) to authenticate users using a PAM service.

Configuration options
=====================

``service`` (optional)
    Name of the PAM service used to perform authentication. If not provided
    the ``login`` service is used by default.
"""

from .. import store


class PAMStore(store.Base):
    def __init__(self, service = None):
        super(PAMStore, self).__init__()
        self._service = service

    def authenticate(self, username, password):
        import simplepam
        return simplepam.authenticate(username, password, self._service)


def from_config(config):
    return PAMStore(config.get("service", None))
