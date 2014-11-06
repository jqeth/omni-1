#! /usr/bin/env python
# -*- coding: utf-8 -*-
# vim:fenc=utf-8
#
# Copyright © 2014 Adrian Perez <aperez@igalia.com>
#
# Distributed under terms of the GPLv3 license.

"""
Implements a store that loads user and passwords from plain text files.

The recognized file format is line-based and compatible with a number of
other text-based user databases. The parser is intentionally forgiving with
unrecognized input lines.
"""

from .. import store
from six import iteritems, iterkeys
from codecs import open
from collections import OrderedDict
import crypt

_crypt_methods = {}
if hasattr(crypt, "methods"):  # pragma: no cover
    for _method in crypt.methods:
        _crypt_methods[_method.name.lower()] = _method
    _crypt_mksalt = crypt.mksalt
else:  # pragma: no cover
    # Patch up missing parts from the crypt module from Python 2.x
    _crypt_methods["crypt"] = "crypt"
    class _crypt_mksalt(object):
        from string import digits, ascii_letters
        _salt_chars = digits + ascii_letters

        def __call__(self, method=None):
            from random import choice
            return choice(self._salt_chars) + choice(self._salt_chars)
    _crypt_mksalt = _crypt_mksalt()


class BaseFileFormat(object):
    def __init__(self, open_func):
        self._users = OrderedDict()
        self._infos = {}
        self._open = open_func

    def __contains__(self, username):
        return username in self._users

    def __getitem__(self, username):
        return self._users[username]

    @property
    def users(self):
        return iterkeys(self._users)

    def add(self, username, password, extrainfo=None):
        if username in self._users:
            raise KeyError("User already exists: {}".format(username))
        self._users[username] = self.crypt_password(username, password)
        if extrainfo:
            assert username not in self._infos
            self._infos[username] = extrainfo
        return self

    def delete(self, username):
        if username in self._users:
            del self._users[username]
            del self._infos[username]
        else:
            raise KeyError("User not found: {}".format(username))

    def __enter__(self):
        with self._open("r") as fd:
            for line in fd.readlines():
                line = line.strip().split(":", 2)
                self._users[line[0]] = line[1]
                if len(line) == 3:
                    self._infos[line[0]] = line[2]
            return self

    def __exit__(self, type_, value, traceback):
        with self._open("w") as fd:
            for u, p in iteritems(self._users):
                x = self._infos.get(u)
                if x is None:
                    fd.write("{}:{}\n".format(u, p))
                else:
                    fd.write("{}:{}:{}\n".format(u, p, x))
        return self

    def crypt_password(self, username, password, salt=None):
        raise NotImplementedError


class PlainFileFormat(BaseFileFormat):
    def crypt_password(self, username, password, salt=None):
        return password


class HtpasswdFileFormat(BaseFileFormat):
    def __init__(self, open_func, method):
        super(HtpasswdFileFormat, self).__init__(open_func)
        self._method = method

    def crypt_password(self, username, password, salt=None):
        if salt is None:
            salt = _crypt_mksalt(self._method)
        return crypt.crypt(password, salt)


class PlainStore(store.Base):
    def __init__(self, path, format_, *fargs):
        super(PlainStore, self).__init__()
        self._format = format_
        self._fargs = fargs
        self._path = path

    def _open_file(self, mode):  # pragma: no cover
        return open(self._path, mode, encoding="utf-8")

    def authenticate(self, username, password):
        with self._format(self._open_file, *self._fargs) as db:
            current = db[username]
            crypted = db.crypt_password(username, password, current)
            return current == crypted


def from_config(config):
    file_format = config.get("format", "plain")
    if file_format == "plain":
        file_format = PlainFileFormat
        format_args = ()
    elif file_format == "htpasswd":
        file_format = HtpasswdFileFormat
        crypt_method = _crypt_methods[config.get("method", "crypt")]
        format_args = (crypt_method,)
    else:
        raise KeyError("File format not supported: {}".format(file_format))

    return PlainStore(config["path"], file_format, *format_args)
