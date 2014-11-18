#! /usr/bin/env python
# -*- coding: utf-8 -*-
# vim:fenc=utf-8
#
# Copyright © 2014 Adrian Perez <aperez@igalia.com>
#
# Distributed under terms of the MIT license.

"""
Authenticates a single user with a fixed password.

An username and password pair is kept in memory to be checked against. A
typical usage of this store is to provide a single user that is known only
by OMNI; for example, to define an user with administrative privileges that
can access the OMNI web interface without restrictions:

.. code-block:: lighttpd
   :linenos:

    stores {
        trivial.omni-admin {
            username "baron"
            password "redtriplane"
        }

        # Other stores...
    }

    http {
        web {
            admin "trivial.omni-admin"
        }
    }


**Configuration options:**

``username``
    Fixed user name.

``password`` (optional)
    Password for the user, in plain text.
"""

from .. import store, valid


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


config_schema = valid.Schema({
    "username": valid.Identifier,
    valid.Optional("password"): valid.Password,
})


@valid.argument(config_schema)
def from_config(config):
    return TrivialStore(config["username"], config.get("password", ""))
