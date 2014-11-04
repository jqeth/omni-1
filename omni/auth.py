#! /usr/bin/env python
# -*- coding: utf-8 -*-
# vim:fenc=utf-8
#
# Copyright © 2014 Adrian Perez <aperez@igalia.com>
#
# Distributed under terms of the GPLv3 license.

"""

"""

class Authenticator(object):
    def authenticate(self, username, password):
        raise NotImplementedError


class Chain(Authenticator, list):
    def authenticate(self, username, password):
        for a in self:
            if a.authenticate(username, password):
                return True
        return False
