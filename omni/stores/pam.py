#! /usr/bin/env python
# -*- coding: utf-8 -*-
# vim:fenc=utf-8
#
# Copyright © 2014 Adrian Perez <aperez@igalia.com>
#
# Distributed under terms of the GPLv3 license.

"""
Authenticates users using PAM.

Uses PAM (via the `simplepam <https://pypi.python.org/pypi/simplepam/>`_
module) to authenticate users using a PAM service. By default, the ``login``
service will be used, which typically authenticates user accounts for the
local machine. You may want to use the ``service`` option to change this:

.. code-block:: lighttpd
   :linenos:

    stores {
        pam.omni {
            service "omni"
        }
    }

With this snippet in the configuration file, the ``/etc/pam.d/omni``
`service definition file
<http://www.linux-pam.org/Linux-PAM-html/sag-configuration-file.html>`__
will be expected to be readable by OMNI.


**Configuration options:**

``service`` (optional)
    Name of the PAM service used to perform authentication. If not provided
    the ``login`` service is used by default.

``min-uid`` (optional)
    Users with an UID smaller that this value will not be useable. This is
    typically used to hide special system users from user listings. The
    default value is `1000`, which is a typical value for GNU/Linux systems
    and some BSD systems as well.
"""

from .. import store
from .. import valid


class PAMStore(store.Base):
    def __init__(self, service=None, min_uid=0):
        super(PAMStore, self).__init__()
        self._service = service
        self._min_uid = min_uid

    def authenticate(self, username, password):
        # XXX: Should we be picky and check for validity of the UID?
        import simplepam
        return simplepam.authenticate(username, password, self._service)

    def usernames(self):
        # FIXME: This works but it might be better to use NSS directly.
        import pwd
        return (pw.pw_name for pw in pwd.getpwall()
                if pw.pw_uid >= self._min_uid)


config_schema = valid.Schema({
    valid.Optional("service"): valid.Identifier,
    valid.Optional("min-uid"): valid.NaturalNumber,
})


@valid.argument(config_schema)
def from_config(config):
    return PAMStore(config.get("service", None), config.get("min-uid", 1000))
