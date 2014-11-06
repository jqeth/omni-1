#! /usr/bin/env python
# -*- coding: utf-8 -*-
# vim:fenc=utf-8
#
# Copyright © 2014 Adrian Perez <aperez@igalia.com>
#
# Distributed under terms of the MIT license.

from setuptools import setup
from setuptools import find_packages
from os import path
from email import parser
from email import message
from re import match
from codecs import open


class Metadata(message.Message, object):
    @staticmethod
    def get_author_field(name, field):
        return match(r"^([^<]+)\s+<([^>]*)>$", name).group(field)
    @staticmethod
    def get_multiline(content):
        return [line.strip() for line in content.splitlines() if line]
    @staticmethod
    def get_sub_keyed(content):
        m = parser.Parser().parsestr(content.strip())
        return dict((k, Metadata.get_multiline(m[k])) for k in m.keys())

    description = property(lambda self: self["Description"])
    version = property(lambda self: self["Version"])
    package = property(lambda self: self["Package"])
    url = property(lambda self: self["URL"])
    license = property(lambda self: self["License"])
    main_author_name = property(lambda self:
            self.get_author_field(self.authors[0], 1))
    main_author_email = property(lambda self:
            self.get_author_field(self.authors[0], 2))
    test_requirements = property(lambda self:
            self.get_multiline(self["Test-Requirements"]))
    extra_requirements = property(lambda self:
            self.get_sub_keyed(self["Extra-Requirements"]))
    entry_points = property(lambda self:
            self.get_multiline(self["Scripts"]))
    requirements = property(lambda self:
            self.get_multiline(self["Requirements"]))
    classifiers = property(lambda self:
            self.get_multiline(self["Classifiers"]))
    authors = property(lambda self: self.get_multiline(self["Authors"]))



def metadata():
    with open(path.join(path.dirname(__file__), "omni", "META"), "rU",
            encoding="utf-8") as f:
        return parser.Parser(Metadata).parse(f)
metadata = metadata()


def file_contents(*relpath):
    with open(path.join(path.dirname(__file__), *relpath), "rU",
            encoding="utf-8") as f:
        return f.read()


if __name__ == "__main__":
    setup(
        name=metadata.package,
        version=metadata.version,
        description=metadata.description,
        long_description=file_contents("README.rst"),
        author=metadata.main_author_name,
        author_email=metadata.main_author_email,
        url=metadata.url,
        packages=find_packages(),
        tests_require=metadata.test_requirements,
        install_requires=metadata.requirements,
        extras_require=metadata.extra_requirements,
        license=metadata.license,
        classifiers=metadata.classifiers,
        test_suite="omni.test",
        include_package_data=True,
        entry_points={ "console_scripts": metadata.entry_points },
    )
