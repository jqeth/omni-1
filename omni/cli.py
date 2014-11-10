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

  server       Starts the OMNI server.
  list-users   Lists users in realm or a store.

See 'omni help <command>' for more information on a specific command.
"""

from .metadata import metadata
from . import app
from six import iteritems, print_


def cmd_list_users(omni_app, realm_or_store):
    """
    Usage: omni list-users <realm-or-store>

    Shows a list of users in a realm or store.

    Options:

      -h, --help            Show this help message.
    """
    if "." in realm_or_store:
        usernames = omni_app.get_store(realm_or_store).usernames
    else:
        usernames = omni_app.get_realm(realm_or_store).usernames
    return sorted(usernames())


def cmd_try_authenticate(config, realm_or_store, username):
    """
    Usage: omni try-authenticate <realm-or-store> <username>

    Tries to authenticate an user interactively agains a given realm
    or a particular store. A zero exit status means that authentication
    succeeded. This command can be useful to debug configurations.

    Options:

      -h, --help            Show this help message.
    """
    from getpass import getpass

    application = app.make_application(config)
    if "." in realm_or_store:
        authenticate = application.get_store(realm_or_store).authenticate
    else:
        authenticate = application.get_realm(realm_or_store).authenticate

    if authenticate(username, getpass("password for {}: ".format(username))):
        return 0
    return 1



def cmd_server(config, http_port=None, http_host=None):
    """
    Usage: omni server [--http-port=PORT --http-host=HOST]

    Options:

      -p, --http-port=PORT  Port in which to serve HTTP requests.
      --http-host=HOST      Host name of IP address to bind to.

      -h, --help            Show this help message.
    """
    from omni import app
    from aiowsgi.compat import asyncio
    import aiowsgi

    # Apply command line overrides.
    if http_host is None:
        http_host = config["http"].get("host", "localhost")
    if http_port is None:
        http_port = config["http"].get("port", 8080)

    wsgi_app = app.make_wsgi_application(config)
    loop = asyncio.get_event_loop()
    aiowsgi.create_server(wsgi_app, loop=loop, host=http_host, port=http_port)
    loop.run_forever()


class ArgBag(dict):
    def __getattr__(self, name):
        return self[name]

def docopt(doc, *args, **kwarg):
    from docopt import docopt as do_docopt
    from textwrap import dedent

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

    call_args = {}
    for name, default, is_args, is_kwarg in iterfargs(command):
        alt_name = "opt_" + name
        if is_args or is_kwarg:
            pass
        elif name == "config":
            call_args[name] = app.load_config(args.opt_config)
        elif name == "omni_app":
            config = app.load_config(args.opt_config)
            call_args[name] = app.make_application(config)
        elif alt_name in cmd_args:
            call_args[name] = cmd_args[alt_name]
        elif name in cmd_args:
            call_args[name] = cmd_args[name]
        else:
            call_args[name] = default

    result = command(**call_args)
    if result is not None:
        from inspect import isgenerator
        if isgenerator(result) or isinstance(result, (list, tuple)):
            for item in result:
                print_(item)
        else:
            raise SystemExit(result)


if __name__ == "__main__":
    main()

