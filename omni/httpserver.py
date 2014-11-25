#! /usr/bin/env python
# -*- coding: utf-8 -*-
# vim:fenc=utf-8
#
# Copyright © 2014 Adrian Perez <aperez@igalia.com>
#
# Distributed under terms of the GPLv3 license.

"""
Exposes a REST-ish authentication interface to OMNI.
"""

from webob.exc import HTTPNotFound
from webob.static import FileApp
from .web import routing
from . import valid, store
from Stache import Stache
from os import path, listdir

ASSETS_DIR = path.abspath(path.join(path.dirname(__file__), \
        "web", "assets"))
TEMPLATE_DIR = path.abspath(path.join(path.dirname(__file__), \
        "web", "templates"))


class StacheCache(Stache):
    def __init__(self):
        super(StacheCache, self).__init__()
        for name in listdir(TEMPLATE_DIR):
            if name.endswith(".mustache"):
                with open(path.join(TEMPLATE_DIR, name), "rU") as f:
                    name = name[:-len(".mustache")]
                    self.add_template(name, f.read())

    def __call__(self, data, template):
        return self.render_template(template, data)

render_stache = StacheCache()


change_pass_schema = valid.Schema({
    "username": valid.And(valid.Identifier,
        error="Invalid user name"),
    "password-old": valid.And(valid.Password, len,
        error="The password cannot be empty"),
    "password-new": valid.And(valid.Password, len,
        error="The password cannot be empty"),
    "password-new-again": valid.And(valid.Password, len,
        error="The password cannot be empty"),
})


class ChangePassword(routing.Routes):

    @routing.route("/{realm:dotid}/change-password", ("GET", "POST"))
    @routing.after(render_stache, "changepassword")
    def change_password_form(self, request, realm):
        data = {
            "pagetitle" : u"Password change",
            "form_url"  : self.url(realm=realm),
            "realm"     : realm,
        }
        realm = self.any_realm(realm)
        if request.method == "POST":
            data["error"] = True
            try:
                params = dict(request.POST.items())
                data["username"] = params["username"]
                params = change_pass_schema.validate(params)
                if not realm.authenticate(params["username"],
                        params["password-old"]):
                    data["message"] = u"Invalid username or password"
                elif not len(params["password-new"]):
                    data["message"] = u"New password cannot be empty"
                elif params["password-new"] != params["password-new-again"]:
                    data["message"] = u"Entered passwords do not match"
                elif params["password-old"] == params["password-new"]:
                    data["message"] = u"New password is the same as the old one"
                else:
                    realm.set_password(params["username"],
                            params["password-new"])
                    data["message"] = u"Password update successfully"
                    data["error"] = False
            except KeyError as e:
                data["message"] = e.message
            except valid.SchemaError as e:
                data["message"] = e.message
            except store.AccessError as e:
                data["message"] = e.message

        return data



class WSGIApplication(routing.Dispatcher):
    def __init__(self, omni):
        super(WSGIApplication, self).__init__()
        self._omni = omni
        self.add_route(self.do_auth)
        self.add_route(self.assets)
        self.plug_routes(ChangePassword().routes)

    def any_realm(self, realm):
        try:
            return self._omni.get_realm_or_store(realm)
        except KeyError:
            raise HTTPNotFound()

    def admin_realm(self, realm):
        return self._omni["omni-admin"]

    @routing.get("/+assets/{filename:str}")
    def assets(self, request, filename):
        return FileApp(path.join(ASSETS_DIR, filename))

    @routing.get("/{realm:dotid}/authenticate")
    @routing.authenticate(any_realm)
    def do_auth(self, request):
        request.response.content_type = "text/plain"
        return "OK\r\n"

    __call__ = routing.Dispatcher.dispatch_wsgi
