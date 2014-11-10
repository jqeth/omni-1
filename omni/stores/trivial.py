#! /usr/bin/env python
# -*- coding: utf-8 -*-
# vim:fenc=utf-8
#
# Copyright © 2014 Adrian Perez <aperez@igalia.com>
#
# Distributed under terms of the MIT license.

"""
Authenticate a single user with a fixed password.

Stores a username and password pair in memory to be checked against.

Configuration options
=====================

``username``
    Fixed user name.

``password`` (optional)
    Password for the user.
"""

from .. import store


class TrivialStore(store.Base):
    def __init__(self, username, password):
        super(TrivialStore, self).__init__()
        self._credentials = (username, password)

    def authenticate(self, username, password):
        return (username, password) == self._credentials

    def usernames(self):
        yield self._credentials[0]


def from_config(config):
    return TrivialStore(config["username"], config.get("password", ""))
