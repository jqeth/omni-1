#! /usr/bin/env python
# -*- coding: utf-8 -*-
# vim:fenc=utf-8
#
# Copyright © 2014 Adrian Perez <aperez@igalia.com>
#
# Distributed under terms of the GPLv3 license.

"""
Provides the root resource of the OMNI Web User Interface

Route Template Syntax
---------------------

Route template strings provide a pattern with wildcards used to match URLs.
URL portions matching wildcards are extracted from the URL and converted
according to optional type annotations.

A template may not specify any wildcards. In that case the URL is matched
literally (e.g. ``foo/bar``).

Wildcards are names enclosed in brackets, e.g. ``{name}``. A type
annotation may optionally follow after a colon, e.g. ``{name:int}``.
Names must be unique for each route, and they must be valid Python
identifiers. Type annotations also determine how values are converted
before being passed to the route callback. The following type
annotations are available:

========== ================= ==============
Annotation Type              Converted Type
========== ================= ==============
``id``     Identifier        ``unicode``
           *(default)*
---------- ----------------- --------------
``dotid``  Identifier which  ``unicode``
           may contain dots
---------- ----------------- --------------
``str``    Arbitrary text    ``unicode``
---------- ----------------- --------------
``int``    Integer           ``int``
---------- ----------------- --------------
``uint``   Unsigned integer  ``int``
========== ================= ==============


As an example, the template ``{item}/{action}`` matches as follows:

========== =======================================
Path       Result
========== =======================================
/123/save  ``{"item": u"123", "action": u"save"}``
/123/save/ *No match.*
/123/      *No match.*
//save     *No match.*
========== =======================================


Module Contents
---------------

"""

from .. import valid
from functools import wraps
from webob.exc import HTTPNotFound, HTTPNotAcceptable, HTTPMethodNotAllowed
from webob.exc import HTTPUnauthorized
from webob.dec import wsgify
from base64 import b64decode
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


def make_tuple(v):
    if isinstance(v, (list, tuple)) or inspect.isgenerator(v):
        return tuple(v)
    else:
        return (v,)


class Route(object):
    """
    Defines a callback to be invoked for a certain URL template.

    See `route template syntax`_ for details on the mini-language accepted
    in URL template strings.

    :param callback: Callable to invoke when the route is matched.
    :param template: Route template string.
    :param methods: HTTP methods handled by this route.
    :param name: Name of the route. May be used to look the route back
        by name.
    """
    def __init__(self, callback, template, methods, name=None):
        s, r, f = parse_route_template(template)
        self.methods  = tuple(sorted((m.upper() for m in make_tuple(methods))))
        self.callback = callback
        self.template = template
        self.name     = name
        self._schema  = s
        self._format  = f
        self._match   = r.match

    def __eq__(self, other):
        # XXX: Probably we want to compare a version of the regexp stripped
        #      of the capture names, to determine whether both routes would
        #      match the same set of URLs.
        return self is other or (isinstance(other, Route)
                and self.methods == other.methods
                and self.template == other.template)

    def __repr__(self):  # pragma: no cover
        return "Route({!r}, {!r}, name={!r})".format(
                self.template, self.methods, self.name)

    def __call__(self, request, *arg, **kw):
        """
        Invokes the route callback.

        :param request: A :class:`webob.Request` instance.
        """
        return self.callback(request, *arg, **kw)

    def make_url(self, base="", **kw):
        """
        Builds a matching URL for the route.

        This method allows to construct valid URLs that would match the
        route template. The passed keyword arguments are used to fill-in
        the wildcards from the template.

        :param base: Base URL used as prefix.
        :param kw: Parameter values.
        :return: URL as a string.
        """
        return base + self._format(**kw)

    def match_url(self, url):
        """
        Try to match an URL against the route template.

        Matches the given `url` agains the route template. On a successful
        match, a dictionary mapping wildcards to the values they matched in
        the `url` is returned. If the `url` does not match the template,
        `None` is returned instead.

        :param url: The URL to be matched.
        :returns: `None` (if unmatched) or `dict` (if matched).
        """
        match = self._match(url)
        return None if match is None else match.groupdict()

    def validate_data(self, data):
        """
        Validate and convert data according to annotations in the template.

        Uses the type annotations from the route template to validate
        a dictionary in which keys are the names of the wildcards, and their
        values are strings. A new dictionary is returned, with the values
        converted accordingly. Typically, this method is used on the data
        dictionary returned by :func:`match_url()`.

        See `route template syntax`_ for details on how conversions are
        performed on the input data.

        If validation fails :class:`omni.valid.SchemaError` is raised.

        :param data: Dictionary with data.
        :returns: New dictionary with data validated and converted.
        """
        return self._schema.validate(data)

    def validate_url(self, url):
        """
        Matches, validates and convert data from an URL in a single step.

        This is equivalent to use :func:`match_url()` followed by
        :func:`validate_data()`. The returned dictionary will contain
        values which are already converted.

        :param url: The URL to be matched.
        :returns: `None` (if unmatched) or `dict` (if matched).
        """
        match = self._match(url)
        if match:
            return self.validate_data(match.groupdict())
        return None


def route(template, method="ANY", name=None):
    """
    Decorates a function as a route.

    :param template: Route template (see `route template syntax`_).
    :param method: HTTP methods for the route, either a single value
        or a list of strings.
    :param name: Name of the route. If not provided, the name of the
        decorated function is used.
    """
    def partial(func):
        return wraps(func)(Route(func, template, method,
            camel_to_under(func.__name__) if name is None else name))
    return partial

def get(template, *arg, **kw):
    """
    Decorates a function as a route, using ``GET`` as method.

    See :func:`route()` for details.
    """
    return route(template, "GET", *arg, **kw)

def post(template, *arg, **kw):
    """
    Decorates a function as a route, using ``POST`` as method.

    See :func:`route()` for details.
    """
    return route(template, "POST", *arg, **kw)

def put(template, *arg, **kw):
    """
    Decorates a function as a route, using ``PUT`` as method.

    See :func:`route()` for details.
    """
    return route(template, "PUT", *arg, **kw)

def delete(template, *arg, **kw):
    """
    Decorates a function as a route, using ``DELETE`` as method.

    See :func:`route()` for details.
    """
    return route(template, "DELETE", *arg, **kw)

def patch(template, *arg, **kw):
    """
    Decorates a function as a route, using ``PATCH`` as method.

    See :func:`route()` for details.
    """
    return route(template, "PATCH", *arg, **kw)


def authenticate(get_realm, realm_param="realm"):
    def partial(func):
        @wraps(func)
        def f(self, request, **kw):
            realm = kw[realm_param]
            del kw[realm_param]
            realm = get_realm(self, realm)
            username = None
            password = None
            if request.authorization:
                password = b64decode(request.authorization[1])
                username, password = password.decode("utf-8").split(":", 1)
            if username is None or not realm.authenticate(username, password):
                raise HTTPUnauthorized(headers=[
                    ("WWW-Authenticate",
                        "Basic realm=\"{}\"".format(realm.description)),
                ])
            return func(self, request, **kw)
        return f
    return partial


class Dispatcher(object):
    """
    Handles dispatching of HTTP requests.
    """
    def __init__(self):
        self.__route_dispatch = {}
        # Give subclasses a chance to override "routes" and get their
        # routes automagically plugged in at instance initialization.
        self.plug_routes(self.routes)

    @property
    def routes(self):
        """
        Enumerate all the `Route` objects known by the dispatcher.

        Accessing this property returns a generator which yields all the
        routes known by this dispatcher.
        """
        seen = set()
        for _, routes in self.__route_dispatch:
            for r in routes:
                if r in seen:
                    continue
                seen.add(r)
                yield r

    def add_route(self, route):
        """
        Adds a route to the dispatcher.

        :param route: An instance of :class:`Route`
        """
        assert isinstance(route, Route)
        # TODO: Check that existing routes won't shadow the URLs
        #       matched by the one being added.
        for method in route.methods:
            if method not in self.__route_dispatch:
                self.__route_dispatch[method] = []
            self.__route_dispatch[method].append(route)

    def plug_routes(self, routes):
        """
        Imports all the routes from another dispatcher.

        Picks the routes known by `other` and plugs them into the dispatcher

        :param routes: Iterable containing :class:`Route` instances.
        """
        for r in routes:
            self.add_route(r)

    def dispatch_request(self, request):
        """
        Dispatches a request to the known routes.

        :param request: A :class:`webob.Request` instance.
        """
        method = request.method.upper()
        path = request.path_info or "/"
        if method == "HEAD":
            try_methods = ("PROXY", method, "GET", "ANY")
        else:
            try_methods = ("PROXY", method, "ANY")

        tried_methods = set()
        for m in try_methods:
            if m in self.__route_dispatch:
                tried_methods.add(m)
                for r in self.__route_dispatch[m]:
                    try:
                        data = r.validate_url(path)
                    except valid.SchemaError as e:
                        raise HTTPNotAcceptable(e)
                    if data:
                        return r(self, request, **data)

        allowed = set()
        tried = set(try_methods)
        for method in set(self.__route_dispatch) - tried:
            for r in self.__route_dispatch[method]:
                if r.match_url(path):
                    allowed.add(method)

        if allowed:
            raise HTTPMethodNotAllowed(headers=[
                ("Allow", ",".join(allowed)),
            ])
        raise HTTPNotFound()

    dispatch_wsgi = wsgify(dispatch_request)
    """Dispatch requests as a WSGI application."""


class Routes(object):
    @property
    def routes(self):
        for _, r in inspect.getmembers(self,
                lambda r: isinstance(r, Route)):
            yield r


class View(Routes):
    template = None

    def __init__(self, template=None):
        super(View, self).__init__()
        if template is None:
            if self.template is None:
                t = camel_to_under(self.__class__.__name__)
                if t.endswith("_view"):
                    t = t[:-5]
                self.template = t
        else:
            self.template = template



__all__ = [
    "Route", "Dispatcher", "Routes", "View",
    "route", "get", "post", "put", "delete", "patch",
]
