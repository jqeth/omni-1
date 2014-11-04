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

class PlainStore(store.Base):
    def __init__(self, path):
        super(PlainStore, self).__init__()
        self._path = path

    def authenticate(self, username, password):
        raise NotImplementedError


def from_config(config):
    return PlainStore(config["path"])
