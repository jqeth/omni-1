#! /usr/bin/env python
# -*- coding: utf-8 -*-
# vim:fenc=utf-8
#
# Copyright © 2014 Adrian Perez <aperez@igalia.com>
#
# Distributed under terms of the MIT license.

"""
Provides the root resource of the OMNI Web User Interface
"""

from .. import valid
from functools import wraps
from webob.exc import HTTPNotFound, HTTPNotAcceptable, HTTPMethodNotAllowed
from webob.dec import wsgify
import re, inspect

camel_to_under_first_cap_sub = re.compile(r"(.)([A-Z][a-z]+)").sub
camel_to_under_all_cap_sub = re.compile(r"([a-z0-9])([A-Z])").sub
camel_to_under = lambda value: \
    camel_to_under_all_cap_sub(r"\1_\2", \
        camel_to_under_first_cap_sub(r"\1_\2", value)).lower()
template_var_re_finditer = \
    re.compile(r"\{(?P<name>[_a-zA-Z][_\w]*)(:(?P<type>[_\w^\d][_\w]*))?\}") \
        .finditer

_schema_map = {
    "int"   : ("d", "(?P<{}>[-+]?\d+)",          valid.Number),
    "uint"  : ("d", "(?P<{}>\d+)",               valid.NaturalNumber),
    "str"   : ("s", "(?P<{}>[^/]+)",             valid.Text),
    "id"    : ("s", "(?P<{}>[_a-zA-Z][_\w]*)",   valid.Identifier),
    "dotid" : ("s", "(?P<{}>[_a-zA-Z][_\.\w]*)", valid.DotIdentifier),
}


def parse_route_template(template):
    """
    parse_route_template(str) -> (Schema, Regexp, str)
    """
    rbuilder = ["^"]
    fbuilder = []
    position = 0
    schema = {}

    for match in template_var_re_finditer(template):
        param_name = match.group("name")
        param_type = match.group("type") or "id"
        # TODO: Handle KeyError, maybe we want to use a custom error here.
        param_formatchar, param_re, param_schema = _schema_map[param_type]
        schema[param_name] = param_schema

        rbuilder.append(re.escape(template[position:match.start()]))
        rbuilder.append(param_re.format(param_name))

        fbuilder.append(template[position:match.start()])
        fbuilder.append("{")
        fbuilder.append(param_name)
        fbuilder.append(":")
        fbuilder.append(param_formatchar)
        fbuilder.append("}")

        position = match.end()

    rbuilder.append(re.escape(template[position:]))
    rbuilder.append("$")
    fbuilder.append(template[position:])

    return (valid.Schema(schema),
            re.compile("".join(rbuilder)),
            u"".join(fbuilder).format)


class Route(object):
    def __init__(self, callback, template, method, name):
        s, r, f = parse_route_template(template)
        self.callback = callback
        self.template = template
        self.method   = method.upper()
        self.name     = name
        self._schema  = s
        self._format  = f
        self._match   = r.match

    def __repr__(self):  # pragma: no cover
        return "Route({!r}, {!r}, name={!r})".format(
                self.template, self.method, self.name)

    def __call__(self, request, *arg, **kw):
        return self.callback(request, *arg, **kw)

    def make_url(self, base="", **kw):
        return base + self._format(**kw)

    def match_url(self, url):
        match = self._match(url)
        return None if match is None else match.groupdict()

    def validate_data(self, data):
        return self._schema.validate(data)

    def validate_url(self, url):
        match = self._match(url)
        if match:
            return self.validate_data(match.groupdict())
        return None


def route(template, method="ANY", name=None):
    def partial(func):
        return wraps(func)(Route(func, template, method, name))
    return partial

def get(template, *arg, **kw):
    return route(template, "GET", *arg, **kw)

def post(template, *arg, **kw):
    return route(template, "POST", *arg, **kw)

def put(template, *arg, **kw):
    return route(template, "PUT", *arg, **kw)

def delete(template, *arg, **kw):
    return route(template, "DELETE", *arg, **kw)

def patch(template, *arg, **kw):
    return route(template, "PATCH", *arg, **kw)


class Resource(object):
    template = None

    def __add_route(self, r):
        if r.method not in self.__rule_dispatch:
            self.__rule_dispatch[r.method] = set()
        self.__rule_dispatch[r.method].add(r)

    def __init__(self):
        if self.template is None:
            t = camel_to_under(self.__class__.__name__)
            if t.endswith("_view"):
                t = t[:-5]
            self.template = t
        self.__rule_dispatch = {}
        for name, r in inspect.getmembers(self,
                lambda r: isinstance(r, Route)):
            if r.name is None:
                r.name = camel_to_under(name)
            self.__add_route(r)

    def dispatch_request(self, request):
        method = request.method.upper()
        path = request.path_info or "/"
        if method == "HEAD":
            try_methods = ("PROXY", method, "GET", "ANY")
        else:
            try_methods = ("PROXY", method, "ANY")

        tried_methods = set()
        for m in try_methods:
            if m in self.__rule_dispatch:
                tried_methods.add(m)
                for r in self.__rule_dispatch[m]:
                    try:
                        data = r.validate_url(path)
                    except valid.SchemaError as e:
                        raise HTTPNotAcceptable(e)
                    if data:
                        return r(self, request, **data)

        allowed = set()
        tried = set(try_methods)
        for method in set(self.__rule_dispatch) - tried:
            for r in self.__rule_dispatch[method]:
                if r.match_url(path):
                    allowed.add(method)

        if allowed:
            raise HTTPMethodNotAllowed(headers=[
                ("Allow", ",".join(allowed)),
            ])
        raise HTTPNotFound()

    dispatch_wsgi = wsgify(dispatch_request)
