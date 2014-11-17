#! /usr/bin/env python
# -*- coding: utf-8 -*-
# vim:fenc=utf-8
#
# Copyright © 2014 Adrian Perez <aperez@igalia.com>
#
# Distributed under terms of the MIT license.

"""
Utilities for dealing with configuration files.
"""

from six import text_type, string_types
from schema import Schema, SchemaError
from schema import Optional, And, Or, Use
from functools import wraps
from os import path


_UNDEFINED = object()


def IPv4Address(value):
    from socket import inet_pton, AF_INET, error
    try:
        inet_pton(AF_INET, value)
        return True
    except error:
        return False


def IPv6Address(value):
    from socket import inet_pton, AF_INET6, error
    try:
        inet_pton(AF_INET6, value)
        return True
    except error:
        return False


def Match(regexp, flags=0):
    import re
    match = re.compile(regexp, flags).match
    @wraps(Match)
    def f(value):
        return match(value) is not None
    return f


Password       = Use(text_type)
Text           = And(text_type, len)
Identifier     = And(text_type, Match(r"^[_a-zA-Z]\w*$"),
                     error="Invalid identifier")
DotIdentifier  = And(text_type, Match(r"^[_\.a-zA-Z][\w\.]*$"),
                     error="Invalid identifier")
Path           = And(Or(text_type, *string_types), Use(path.realpath),
                     error="Invalid path")
Number         = Use(int)
NaturalNumber  = And(Number, lambda v: v >= 0, error="Not a positive number")
PortNumber     = And(Number, lambda v: 0 < v <= 65535)
Hostname       = Match(r"^[\w][\.\w]*$")
NetworkAddress = Or(IPv4Address, IPv6Address, Hostname)


def argument(schema, name=None):
    def decorate(func):
        if name is None:
            @wraps(func)
            def wrapper(data, *arg, **kw):
                return func(schema.validate(data, *arg, **kw))
        else:
            # TODO: Implement calling the function with validation done for the
            #       given named argument.
            raise NotImplementedError
        return wrapper
    return decorate
