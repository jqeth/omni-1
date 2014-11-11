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
from .. import config

class TrivialStore(store.Base):
    readonly = False

    def __init__(self, username, password):
        super(TrivialStore, self).__init__()
        self._credentials = (username, password)

    def authenticate(self, username, password):
        return (username, password) == self._credentials

    def usernames(self):
        yield self._credentials[0]

    def set_password(self, username, password):
        if username != self._credentials[0]:
            raise KeyError("invalid username {}".format(username))
        self._credentials = (username, password)


@config.schema
def config_schema():
    return {
        "username": config.Identifier,
        config.Optional("password"): config.Password,
    }


def from_config(config):
    config = config_schema.validate(config)
    return TrivialStore(config["username"], config.get("password", ""))
