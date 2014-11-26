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
from inspect import isgenerator
from six import iteritems


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

    def set_password(self, username, password):
        """
        Set a new password for the given user.
        """
        raise NotImplementedError

    def has_user(self, username):
        """
        Checks whether the store knows about a given user.
        """
        try:
            return self.get_user(username) is not None
        except NotImplementedError:
            for u in self.usernames():
                if u == username:
                    return True
            return False

    def get_user(self, username):
        """
        Obtains the details for a given user name.
        """
        raise NotImplementedError


class AccessError(Exception):
    """
    Raised when a store or realm cannot be accessed in the requested way.
    """
    pass


class Realm(Authenticator, list):
    """
    A realm is a list of `Authenticator` objects which are tried in order.
    """
    def __init__(self, description, *realms):
        if len(realms) == 1 and isgenerator(realms[0]):
            super(Realm, self).__init__()
            self.extend(realms[0])
        else:
            super(Realm, self).__init__(realms)
        self.description = description

    def authenticate(self, username, password):
        for a in self:
            if a.has_user(username):
                return a.authenticate(username, password)
        raise KeyError("user {} does not exist".format(username))

    def usernames(self):
        seen = set()
        for a in self:
            for username in a.usernames():
                if username in seen:
                    continue
                seen.add(username)
                yield username

    def set_password(self, username, password):
        for a in self:
            if a.has_user(username):
                if a.readonly:
                    raise AccessError("user {} belongs is in a read-only store"
                            .format(username))
                a.set_password(username, password)
                return
        raise KeyError("user {} does not exist".format(username))

    def has_user(self, username):
        for a in self:
            if a.has_user(username):
                return True
        return False

    def get_user(self, username):
        for a in self:
            if a.has_user(username):
                return a.get_user(username)
        raise KeyError("user {} does not exist".format(username))


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

    def get_realm_or_store(self, name):
        if "." in name:
            return self.get_store(name)
        else:
            return self.get_realm(name)

    def __contains__(self, name):
        return name in self._realms

    def __getitem__(self, name):
        return self._realms[name]

    @property
    def stores(self):
        """
        Provides an iterator over `(name, store)` pairs.
        """
        return iteritems(self._stores)

    @property
    def realms(self):
        """
        Provides an iterator over `(name, realm)` pairs.
        """
        return iteritems(self._realms)



def find(storename):
    from importlib import import_module
    import omni.stores
    return import_module("." + storename, "omni.stores")
