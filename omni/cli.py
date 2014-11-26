#! /usr/bin/env python
# -*- coding: utf-8 -*-
# vim:fenc=utf-8
#
# Copyright © 2014 Adrian Perez <aperez@igalia.com>
#
# Distributed under terms of the GPLv3 license.

"""
Usage: omni [--version] [--config=<path>] <command> [<args>...]

Options:

  -C, --config=PATH  Path to comfiguration file [default: /etc/omni.conf].
  --version          Show the OMNI version and exit.
  -h, --help         Show this help message.

The most commonly used commands are:

  server           Starts the OMNI server.
  list-stores      Lists the configured stores.
  list-realms      Lists the configured realms.
  list-users       Lists users in realm or a store.
  create-user      Adds an user to a realm or a store.
  delete-user      Deletes an user from a realm or a store.
  change-password  Changes the passform for an user.
  help             Show help about different topics.

See 'omni help <command>' for more information on a specific command.
"""

from .metadata import metadata
from . import app, valid
from six import iteritems, print_
from textwrap import dedent
import wcfg


def cmd_list_stores(omni_app):
    """
    Usage: omni list-stores

    Shows a list of configured stores.

    Options:

      -h, --help  Show this help message.
    """
    return sorted((name for name, _ in omni_app.stores))


def cmd_list_realms(omni_app):
    """
    Usage: omni list-realms

    Shows a list of configured realms.

    Options:

      -h, --help  Show this help message.
    """
    return sorted((name for name, _ in omni_app.realms))


def cmd_list_users(omni_app, realm_or_store):
    """
    Usage: omni list-users <realm-or-store>

    Shows a list of users in a realm or store.

    Options:

      -h, --help  Show this help message.
    """
    try:
        return sorted(omni_app.get_realm_or_store(realm_or_store).usernames())
    except KeyError:
        return "{}: invalid realm/store".format(realm_or_store)


def cmd_create_user(omni_app, realm_or_store, username, opt_stdin=False,
        opt_prompt_password=False):
    """
    Usage: omni create-user [options] <realm-or-store> <username>

    Adds a new user to a realm or a store.

    Options:

      -p, --prompt-password  Prompt for a password.
      -i, --stdin            Read password from standard input.
      -h, --help             Show this help message.
    """
    try:
        db = omni_app.get_realm_or_store(realm_or_store)
    except KeyError:
        return "{}: invalid realm/store".format(realm_or_store)

    if opt_stdin:
        from sys import stdin
        new_pw = stdin.readline().strip()
    elif opt_prompt_password:
        from getpass import getpass
        old_pw = getpass("password for {}: ".format(username))
        new_pw = getpass("password for {} (again): ".format(username))
        if old_pw != new_pw:
            return "passwords do not match"
    else:
        # TODO: Generate passwords and report them somehow. Alternatively,
        #       produce an activation link when we have that plug-in.
        new_pw = "#*" + username + "*#"

    try:
        return db.create_user(username, password=new_pw)
    except NotImplementedError:
        return "{}: user creation not suported".format(realm_or_store)


def cmd_delete_user(omni_app, realm_or_store, username):
    """
    Usage: omni delete-user <realm-or-store> <username>

    Deletes an user from a realm or a store.

    Options:

      -h, --help  Show this help message.
    """
    try:
        db = omni_app.get_realm_or_store(realm_or_store)
    except KeyError:
        return "{}: invalid realm/store".format(realm_or_store)
    try:
        db.delete_user(username)
    except KeyError:
        return "{}: unknown user".format(realm_or_store)
    except NotImplementedError:
        return "{}: user deletion not supported".format(realm_or_store)

def cmd_try_authenticate(omni_app, realm_or_store, username):
    """
    Usage: omni try-authenticate <realm-or-store> <username>

    Tries to authenticate an user interactively agains a given realm
    or a particular store. A zero exit status means that authentication
    succeeded. This command can be useful to debug configurations.

    Options:

      -h, --help  Show this help message.
    """
    from getpass import getpass
    try:
        authenticate = omni_app.get_realm_or_store(realm_or_store).authenticate
    except KeyError:
        return "{}: invalid realm/store".format(realm_or_store)

    if authenticate(username, getpass("password for {}: ".format(username))):
        return 0
    return 1


def cmd_change_password(omni_app, realm_or_store, username, opt_stdin=False):
    """
    Usage: omni change-password <realm-or-store> <username>

    Options:

      -i, --stdin  Read passwords from standard input. The first line must
                   be the existing password, and the second line the new
                   password.
      -h, --help   Show this help message.
    """
    from getpass import getpass
    try:
        db = omni_app.get_realm_or_store(realm_or_store)
    except KeyError:
        return "{}: invalid realm/store".format(realm_or_store)

    if opt_stdin:
        from sys import stdin
        old_pw = stdin.readline().strip()
        if not db.authenticate(username, old_pw):
            return "Incorrect password"
        new_pw = stdin.readline().strip()
    else:
        old_pw = getpass("old password for {}: ".format(username))
        if not db.authenticate(username, old_pw):
            return "Incorrect password"
        old_pw = getpass("new password for {}: ".format(username))
        new_pw = getpass("new password for {} (again): ".format(username))
        if old_pw != new_pw:
            return "Passwords do not match"
    db.set_password(username, new_pw)


config_http_schema = valid.Schema({
    valid.Optional("host"): valid.NetworkAddress,
    valid.Optional("port"): valid.PortNumber,
})


def cmd_server(omni_config, http_port=None, http_host=None, debugger=False):
    """
    Usage: omni server [--http-port=PORT] [--http-host=HOST] [--debugger]

    Options:

      -p, --http-port=PORT  Port in which to serve HTTP requests.
      --http-host=HOST      Host name of IP address to bind to.
      --debugger            Enable the debugger [default: False].

      -h, --help            Show this help message.
    """
    from aiowsgi.compat import asyncio
    import aiowsgi
    import logging
    logging.basicConfig()

    # Apply command line overrides.
    if http_host is None or http_port is None:
        http_config = { "port": 8080, "host": "localhost" }
        if "http" in omni_config:
            conf = config_http_schema.validate(omni_config["http"])
            http_config.update(conf)
        if http_host is None:
            http_host = http_config["host"]
        if http_port is None:
            http_port = http_config["port"]

    omni = app.make_application(omni_config)
    wsgi_app = app.make_wsgi_application(omni)

    if debugger:
        from backlash import DebuggedApplication
        from webob import Request
        from wsgiref.simple_server import make_server

        def getctx(e=None):
            req = None if e is None else Request(e)
            return { "env": e, "omni": omni, "req": req, "app": wsgi_app }

        wsgi_app = DebuggedApplication(wsgi_app,
                context_injectors=[getctx],
                console_init_func=getctx)
        make_server(http_host, http_port, wsgi_app).serve_forever()
    else:
        loop = asyncio.get_event_loop()
        aiowsgi.create_server(wsgi_app, loop=loop,
                host=http_host, port=http_port)
        try:
            loop.run_forever()
        except KeyboardInterrupt:
            pass


def cmd_help(commands, topics, topic):
    """
    Usage: omni help (topics | commands | <topic>)

    Shows information about a commands or about a help topic.

    Options:

      -h, --help  Show this help message.

    """
    if topics:
        return 0
    if commands:
        return sorted((k[4:].replace("_", "-")
            for k, v in iteritems(globals())
            if k != "cmd_help" and k.startswith("cmd_") and callable(v)))

    command = globals().get("cmd_" + topic.replace("-", "_"), None)
    if command is None:
        return "topic or command does not exist: {}".format(topic)

    from docopt import docopt as do_docopt
    do_docopt(dedent(command.__doc__), argv=[topic, "--help"])


class ArgBag(dict):
    def __getattr__(self, name):
        return self[name]

def docopt(doc, *args, **kwarg):
    from docopt import docopt as do_docopt

    args = do_docopt(dedent(doc), *args, **kwarg)
    result = ArgBag()
    for k, v in iteritems(args):
        if k.startswith("--"):
            k = "opt_" + k[2:]
        elif k.startswith("<") and k.endswith(">"):
            k = k[1:-1]
        result[k.lower().replace("-", "_")] = v
    return result


def iterfargs(func):
    from inspect import getargspec
    from six.moves import zip
    args, varargs, varkw, defaults = getargspec(func)
    num_defaults = 0 if defaults is None else len(defaults)

    if num_defaults > 0:
        for var in args[:-num_defaults]:
            yield (var, None, False, False)
        for var, default in zip(args[-num_defaults:], defaults):
            yield (var, default, False, False)
    else:
        for var in args:
            yield (var, None, False, False)
    if varargs is not None:
        yield (varargs, (), True, False)
    if varkw is not None:
        yield (varkw, {}, False, True)


def main():
    args = docopt(__doc__, version=metadata.version, options_first=True)
    command = globals().get("cmd_" + args.command.replace("-", "_"), None)
    if command is None:
        raise SystemExit("'{}' is not a valid command, see 'omni help'."
                .format(args.command))

    # Parse command line options for the subcommand.
    cmd_args = docopt(command.__doc__, argv=[args.command] + args.args)
    try:
        omni_config = None
        call_args = {}
        for name, default, is_args, is_kwarg in iterfargs(command):
            alt_name = "opt_" + name
            if is_args or is_kwarg:
                pass
            elif name == "omni_config":
                if omni_config is None:
                    omni_config = app.load_config(args.opt_config)
                call_args[name] = omni_config
            elif name == "omni_app":
                if omni_config is None:
                    omni_config = app.load_config(args.opt_config)
                call_args[name] = app.make_application(omni_config)
            elif alt_name in cmd_args:
                call_args[name] = cmd_args[alt_name]
            elif name in cmd_args:
                call_args[name] = cmd_args[name]
            else:
                call_args[name] = default

        result = command(**call_args)
    except wcfg.ParseError as e:
        raise SystemExit("error parsing config file:\n{s}:{!s}"
                .format(args.opt_config, e))
    except valid.SchemaError as e:
        raise SystemExit("configuration file validation error:\n{!s}"
                .format(e))

    if result is not None:
        from inspect import isgenerator
        if isgenerator(result) or isinstance(result, (list, tuple)):
            for item in result:
                print_(item)
        else:
            raise SystemExit(result)


if __name__ == "__main__":
    main()

