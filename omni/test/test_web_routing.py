#! /usr/bin/env python
# -*- coding: utf-8 -*-
# vim:fenc=utf-8
#
# Copyright © 2014 Adrian Perez <aperez@igalia.com>
#
# Distributed under terms of the MIT license.

from ..web import routing
from .. import valid
from webob import Request
from webob.exc import HTTPNotFound, HTTPMethodNotAllowed
from six import iteritems
import unittest
import re

sanitize_ident_re_sub = re.compile(r"[^_a-zA-Z0-9]").sub
sanitize_ident = lambda v: \
        str(sanitize_ident_re_sub("_", v).encode("ascii", "replace"))


class TestCamelCaseConverter(unittest.TestCase):

    def test_camel_case_to_unserscored(self):
        data = (
            (u"CamelCase", u"camel_case"),
            (u"camelCaseInTheMiddle", u"camel_case_in_the_middle"),
            (u"nocasechange", "nocasechange"),
            (u"keep_under_scores", "keep_under_scores"),
            (u"MultipleCAPSTogether", "multiple_caps_together"),
            (u"CAPSTogetherPrefix", u"caps_together_prefix"),
            (u"SuffixTogetherCAPS", u"suffix_together_caps"),
        )
        for camel_case, under_score in data:
            self.assertEqual(under_score,
                    routing.camel_to_under(camel_case))


class TestRoute(unittest.TestCase):

    def setUp(self):
        self.r = routing.Route(self.callback,
                u"static/{variable}/morestatic",
                "GET", "testroute")
        self.callback_called = False
        self.last_variable = None
        self.last_request = None

    def callback(self, request, variable):
        self.callback_called = True
        self.last_variable = variable
        self.last_request = request

    def test_route_callback(self):
        req = Request.blank(u"static/VALUE/morestatic")
        self.r(req, variable=u"VALUE")
        self.assertTrue(self.callback_called)
        self.assertTrue(self.last_request is req)
        self.assertEqual(u"VALUE", self.last_variable)

    def test_route_make_url(self):
        self.assertEqual(u"static/VAR/morestatic",
                self.r.make_url(variable=u"VAR"))

    def test_route_match_url(self):
        self.assertEqual(None, self.r.match_url(u"static/morestatic"))
        v = self.r.match_url(u"static/foo/morestatic")
        self.assertTrue(isinstance(v, dict))
        self.assertTrue("variable" in v)
        self.assertEqual(u"foo", v["variable"])

    def test_route_validate_valid_data(self):
        valid_data = (
            u"VAR",  # Unicode string.
            u"FOO",  # Normal string should be converted to Unicode.
            u"a_b",  # Underscores should work.
            u"_123", # Also, numbers preceded with underscores.
        )
        for expected in valid_data:
            url = u"static/{}/morestatic".format(expected)
            v = self.r.validate_url(url)
            self.assertTrue(isinstance(v, dict))
            self.assertTrue("variable" in v)
            self.assertEqual(expected, v["variable"])

    def test_route_validate_invalid_data(self):
        invalid_data = (
            4.12,    # Float numbers must not match.
            123,     # Same with numbers.
            "a.b",   # Dotted identifiers.
            "-+:\\", # Dashes and other symbols.
        )
        for data in invalid_data:
            url = u"static/{}/morestatic".format(data)
            v = self.r.validate_url(url)
            self.assertEqual(None, v)

    def test_route_multiple_methods(self):
        r = routing.Route(self.callback,
                u"get-or-post/{variable}",
                ("GET", "POST"), "testroute")
        self.assertEqual(["GET", "POST"], sorted(r.methods))


class TestRouteSchemaValidation(unittest.TestCase):

    test_data = {
        "int": {
            "valid": (12, -5),
            "invalid": (2.34, -3.4, 1e-34, "blah"),
        },
        "uint": {
            "valid": (0, 1, 23, 42, 1000101),
            "invalid": (-1, -43, -3.4, 2.34, 1e-34, "blah"),
        },
        "str": {
            "valid": (
                u"☺→",   # Some funky Unicode
                u"foo",  # Normal stuff
                u":-\\", # Arbitrary non-slash ASCII characters
            ),
            "invalid": (),
        },
        "dotid": {
            "valid": (
                u"foo.bar",
                u"foo.123",
                u"_24.foo",
                u"_23.321",
                u"_",
                u"_1",
            ),
            "invalid": (
                u"1",
                u"123.321",
            ),
        },
    }

    @staticmethod
    def make_test_valid(typename, value):
        fname = u"test_valid_{}_{!s}".format(typename, value)
        def f(self):
            r = routing.Route(lambda *arg, **kw: None,
                    u"item/{{value:{}}}".format(typename),
                    "GET", "testroute")
            v = r.validate_url(u"item/{!s}".format(value))
            self.assertTrue(isinstance(v, dict))
            self.assertTrue("value" in v)
            self.assertEqual(value, v["value"])
        return sanitize_ident(fname), f

    @staticmethod
    def make_test_invalid(typename, value):
        fname = u"test_invalid_{}_{!s}".format(typename, value)
        def f(self):
            r = routing.Route(lambda *arg, **kw: None,
                    u"item/{{value:{}}}".format(typename),
                    "GET", "testroute")
            # Either validation may return None, if the URL is
            # not matched, or the conversion from strings to
            # Python typed fails with valid.SchemaError.
            try:
                v = r.validate_url(u"item/{!s}".format(value))
                self.assertEqual(None, v)
            except valid.SchemaError:
                pass
        return sanitize_ident(fname), f

    @classmethod
    def inject_test_functions(cls):
        for name, kinds in iteritems(cls.test_data):
            for value in kinds["valid"]:
                setattr(cls, *cls.make_test_valid(name, value))
            for value in kinds["invalid"]:
                setattr(cls, *cls.make_test_invalid(name, value))

TestRouteSchemaValidation.inject_test_functions()



class TestableResource(routing.Routes, routing.Dispatcher):

    @routing.get("get/{variable}")
    def get_variable(self, request, variable):
        return self, request, variable

    @routing.route("head/{variable}", method="HEAD")
    def head_variable(self, request, variable):
        return self, request, variable

    @routing.post("post/{variable}")
    def post_variable(self, request, variable):
        return self, request, variable

    @routing.patch("patch/{variable}")
    def patch_variable(self, request, variable):
        return self, request, variable

    @routing.put("put/{variable}")
    def put_variable(self, request, variable):
        return self, request, variable

    @routing.delete("delete/{variable}")
    def delete_variable(self, request, variable):
        return self, request, variable

    @routing.route("any/{variable}")
    def any_variable(self, request, variable):
        return self, request, variable


class TestResource(unittest.TestCase):

    def setUp(self):
        self.rsrc = TestableResource()

    @staticmethod
    def make_method_dispatch_test(method):
        url = method.lower() + "/foo"
        def f(self):
            req = Request.blank(url, {"REQUEST_METHOD": method})
            r, rreq, rvar = self.rsrc.dispatch_request(req)
            self.assertEqual(self.rsrc, r)
            self.assertEqual(req, rreq)
            self.assertEqual("foo", rvar)
        return "test_dispatch_method_" + method, f

    @staticmethod
    def make_method_dispatch_any_test(method):
        def f(self):
            req = Request.blank("any/bar", {"REQUEST_METHOD": method})
            r, rreq, rvar = self.rsrc.dispatch_request(req)
            self.assertEqual(self.rsrc, r)
            self.assertEqual(req, rreq)
            self.assertEqual("bar", rvar)
        return "test_dispatch_method_any_" + method, f

    @classmethod
    def inject_test_functions(cls):
        for method in ("get", "post", "patch", "put", "delete", "head"):
            setattr(cls, *cls.make_method_dispatch_test(method))
            setattr(cls, *cls.make_method_dispatch_any_test(method))

    def test_dispatch_head_to_get(self):
        req = Request.blank("get/thisishead", {"REQUEST_METHOD": "HEAD"})
        r, rreq, rvar = self.rsrc.dispatch_request(req)
        self.assertEqual(self.rsrc, r)
        self.assertEqual(req, rreq)
        self.assertEqual("thisishead", rvar)

    def test_dispatch_not_found(self):
        req = Request.blank("/")
        with self.assertRaises(HTTPNotFound):
            self.rsrc.dispatch_request(req)

    def test_dispatch_invalid_method(self):
        req = Request.blank("get/bar", {"REQUEST_METHOD": "PATCH"})
        with self.assertRaises(HTTPMethodNotAllowed):
            self.rsrc.dispatch_request(req)

TestResource.inject_test_functions()
