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


class Metadata(message.Message, object):
    @staticmethod
    def get_author_field(name, field):
        return match(r"^([^<]+)\s+<([^>]*)>$", name).group(field)
    def get_multiline(self, name):
        return [line.strip() for line in self[name].splitlines() if line]

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
            self.get_multiline("Test-Requirements"))
    requirements = property(lambda self: self.get_multiline("Requirements"))
    classifiers = property(lambda self: self.get_multiline("Classifiers"))
    authors = property(lambda self: self.get_multiline("Authors"))



def metadata():
    with open(path.join(path.dirname(__file__), "omni", "META"), "rU",
            encoding="utf-8") as f:
        return parser.Parser(Metadata).parse(f)
metadata = metadata()


def file_contents(*relpath):
    with open(path.join(path.dirname(__file__), *relpath), "rU",
            encoding="utf-8") as f:
        return f.read()


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
    license=metadata.license,
    classifiers=metadata.classifiers,
    test_suite="omni.test",
    include_package_data=True,
    entry_points={
        "console_scripts": [
            "omnid = omni.omnid:main",
        ],
    },
)
