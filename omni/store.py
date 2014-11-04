#! /usr/bin/env python
# -*- coding: utf-8 -*-
# vim:fenc=utf-8
#
# Copyright © 2014 Adrian Perez <aperez@igalia.com>
#
# Distributed under terms of the MIT license.

"""

"""

from . import auth


class Base(auth.Authenticator):
    """Whether this store is read-only."""
    readonly = True


def find(storename):
    from importlib import import_module
    import omni.stores
    return import_module("." + storename, "omni.stores")

