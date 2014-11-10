#! /usr/bin/env python
# -*- coding: utf-8 -*-
# vim:fenc=utf-8
#
# Copyright © 2014 Adrian Perez <aperez@igalia.com>
#
# Distributed under terms of the GPLv3 license.

"""
Credential store definition and related utilities.
"""

class Authenticator(object):
    """
    Defines the basic interface for authenticating users.
    """
    def authenticate(self, username, password):
        """
        Authenticates a given user

        :username: Name of the user.
        :password: Password for the user.
        """
        raise NotImplementedError

    def usernames(self):
        """
        Returns an iterator yielding known user names.
        """
        raise NotImplementedError


class Realm(Authenticator, list):
    """
    A realm is a list of `Authenticator` objects which are tried in order.
    """
    def __init__(self, description, *arg):
        super(Realm, self).__init__(*arg)
        self.description = description

    def authenticate(self, username, password):
        for a in self:
            if a.authenticate(username, password):
                return True
        return False

    def usernames(self):
        seen = set()
        for a in self:
            for username in a.usernames():
                if username in seen:
                    continue
                seen.add(username)
                yield username


class Base(Authenticator):
    """
    Base class for authentication stores.
    """
    readonly = True


class OMNI(object):
    def __init__(self):
        self._stores = {}
        self._realms = {}

    def add_store(self, name, store):
        if name in self._stores:
            raise KeyError("Store {} is already present".format(name))
        assert isinstance(store, Base)
        self._stores[name] = store

    def add_realm(self, name, realm):
        if name in self._realms:
            raise KeyError("Realm {} is already present".format(name))
        assert isinstance(realm, Realm)
        self._realms[name] = realm

    def get_realm(self, name):
        return self._realms[name]

    def get_store(self, name):
        return self._stores[name]

    def __contains__(self, name):
        return name in self._realms

    def __getitem__(self, name):
        return self._realms[name]


def find(storename):
    from importlib import import_module
    import omni.stores
    return import_module("." + storename, "omni.stores")
