#! /usr/bin/env python
# -*- coding: utf-8 -*-
# vim:fenc=utf-8
#
# Copyright © 2014 Adrian Perez <aperez@igalia.com>
#
# Distributed under terms of the GPLv3 license.

from ..stores import plain
from .. import store
from textwrap import dedent
from six import StringIO
import unittest


class StringIOWithContext(StringIO, object):
    def __init__(self, persistent, data=None):
        super(StringIOWithContext, self).__init__(data)
        self.persistent = persistent

    def __enter__(self):
        return self

    def __exit__(self, type_, value, traceback):
        self.persistent.data = self.getvalue()


class PersistentStringIO(object):
    def __init__(self, data=""):
        self.data = data

    def __call__(self, mode):
        if "w" in mode:
            return StringIOWithContext(self)
        else:
            return StringIOWithContext(self, self.data)


class TestPlainStoreUnimplementeds(unittest.TestCase):

    def test_format_crypt_password(self):
        f = plain.BaseFileFormat(lambda mode: None)
        with self.assertRaises(NotImplementedError):
            f.crypt_password("user", "pass")


class TestPlainStoreFileFormat(unittest.TestCase):

    def setUp(self):
        self.last_io = None

    def tearDown(self):
        self.last_io = None

    def userdb_string(self, data):
        self.last_io = PersistentStringIO(dedent(data))
        return plain.PlainFileFormat(self.last_io)

    data01 = u"""\
    bob:b0b
    alice:4l1c3
    """

    def test_user_list(self):
        with self.userdb_string(self.data01) as db:
            self.assertEqual(list(db.users), ["bob", "alice"])

    def test_user_exists(self):
        with self.userdb_string(self.data01) as db:
            self.assertTrue("bob" in db)
            self.assertTrue(db.__contains__("bob"))
            self.assertFalse("peter" in db)
            self.assertFalse(db.__contains__("peter"))

    def test_user_get(self):
        with self.userdb_string(self.data01) as db:
            self.assertTrue(db["bob"])
            self.assertTrue(len(db["bob"]) > 0)
            self.assertEqual("b0b", db["bob"])

    def test_user_add(self):
        with self.userdb_string(self.data01) as db:
            db.add("andrew", "andr3w")
            self.assertTrue("andrew" in db)
            self.assertEqual("andr3w", db["andrew"])
        expected = dedent(self.data01).strip()
        expected += "\nandrew:andr3w\n"
        self.assertEqual(expected, self.last_io.data)

    def test_user_add_with_extrainfo(self):
        with self.userdb_string(self.data01) as db:
            db.add("andrew", "andr3w", "Some extra, ignored info")
            self.assertTrue("andrew" in db)
            self.assertEqual("andr3w", db["andrew"])
        expected = dedent(self.data01).strip()
        expected += "\nandrew:andr3w:Some extra, ignored info\n"
        self.assertEqual(expected, self.last_io.data)

    def test_user_add_existing(self):
        with self.userdb_string(self.data01) as db:
            with self.assertRaises(KeyError):
                db.add("bob", "meh")

    def test_user_delete(self):
        with self.userdb_string(self.data01) as db:
            db.delete("bob")
            self.assertFalse("bob" in db)
        self.assertEqual("alice:4l1c3\n", self.last_io.data)

    def test_user_delete_nonexisting(self):
        with self.userdb_string(self.data01) as db:
            with self.assertRaises(KeyError):
                db.delete("peter")
        expected = dedent(self.data01)
        self.assertEqual(expected, self.last_io.data)

    def test_user_crypt_password(self):
        with self.userdb_string(self.data01) as db:
            self.assertEqual("b0b", db.crypt_password("bob", "b0b", db["bob"]))

    data02 = u"""\
    peter:p3t3r:Extra info
    bob:b0b:
    alice:4l1c3
    """

    def test_extrainfo_roundtrip(self):
        with self.userdb_string(self.data02) as db:
            pass
        self.assertEqual(dedent(self.data02), self.last_io.data)

    def test_list_usernames(self):
        with self.userdb_string(self.data02) as db:
            self.assertEqual(["peter", "bob", "alice"], list(db.users))


class TestHtpasswdStoreFormat(unittest.TestCase):

    def setUp(self):
        self.last_io = None

    def tearDown(self):
        self.last_io = None

    def userdb_string(self, data, method):
        m = plain._crypt_methods.get(method, None)
        if m is None:
            self.skipTest(("Crypt method '{}' is not supported by this"
                " Python version").format(method))
        self.last_io = PersistentStringIO(dedent(data))
        return plain.HtpasswdFileFormat(self.last_io, m)


    # Generated with: printf "alice:$(openssl passwd -crypt mirror)" 
    data01 = (u"""\
    alice:su7aWQyEG4lo.
    """, "crypt")

    def test_user_crypt_check_password(self):
        with self.userdb_string(*self.data01) as db:
            self.assertEqual(db["alice"],
                    db.crypt_password("alice", "mirror", db["alice"]))

    def test_user_crypt_check_password_invalid(self):
        with self.userdb_string(*self.data01) as db:
            self.assertNotEqual(db["alice"],
                    db.crypt_password("alice", "hatter", db["alice"]))

    def test_user_crypt_newpassword(self):
        with self.userdb_string(*self.data01) as db:
            old_crypted_pw = db["alice"]
            new_crypted_pw = db.crypt_password("alice", "mirror")
            # If we don't pass the salt (or the existing crypted password),
            # a new crupted password one will be created with a new salt.
            self.assertNotEqual(old_crypted_pw, new_crypted_pw)

    def test_list_usernames(self):
        with self.userdb_string(*self.data01) as db:
            self.assertEqual(["alice"], list(db.users))


class TestPlainStoreInstatiation(unittest.TestCase):

    valid_confs = (
        { "path": "path/to/passwd" },
        { "path": "path/to/passwd", "format": "plain" },
        { "path": "path/to/passwd", "format": "htpasswd" },
        { "path": "path/to/passwd", "format": "htpasswd", "method": "crypt" },
    )

    def test_from_valid_conf(self):
        for conf in self.valid_confs:
            s = plain.from_config(conf)
            self.assertTrue(isinstance(s, store.Base))

    invalid_confs = (
        # No "path" key.
        { },
        # Invalid "format" values.
        { "path": "path/to/passwd", "format": "" },
        { "path": "path/to/passwd", "format": 42 },
        { "path": "path/to/passwd", "format": True },
        { "path": "path/to/passwd", "format": 3.14 },
        { "path": "path/to/passwd", "format": "bogus" },
        # Invalid "crypt" methods for htpasswd format
        { "path": "path/to/passwd", "format": "htpasswd", "method": "" },
        { "path": "path/to/passwd", "format": "htpasswd", "method": 42 },
        { "path": "path/to/passwd", "format": "htpasswd", "method": True },
        { "path": "path/to/passwd", "format": "htpasswd", "method": 3.14 },
        { "path": "path/to/passwd", "format": "htpasswd", "method": "bogus" },
        # The configuration dictionary is strictly checked, and keys
        # which are of not interest for instantiation cause errors.
        { "path": "path/to/passwd", "pi": 3.14 },
    )

    def test_from_invalid_conf(self):
        for conf in self.invalid_confs:
            with self.assertRaises(Exception):
                s = plain.from_config(conf)
                self.assertTrue(isinstance(s, plain.PlainStore))

    def test_find_store(self):
        self.assertEqual(plain, store.find("plain"))


class TestablePlainStore(plain.PlainStore):
    def __init__(self, data, path, format_, *fargs):
        super(TestablePlainStore, self).__init__(path, format_, *fargs)
        self.last_io = PersistentStringIO(dedent(data))

    def _open_file(self, mode):
        return self.last_io(mode)


class TestPlainStoreAuthentication(unittest.TestCase):

    plain_data = TestPlainStoreFileFormat.data01
    crypt_data = TestHtpasswdStoreFormat.data01[0]

    def test_plain_authenticate_success(self):
        s = TestablePlainStore(self.plain_data, "path/to/file",
                plain.PlainFileFormat)
        self.assertTrue(s.authenticate("bob", "b0b"))

    def test_plain_authenticate_failure(self):
        s = TestablePlainStore(self.plain_data, "path/to/file",
                plain.PlainFileFormat)
        self.assertFalse(s.authenticate("bob", "badpass"))

    def test_plain_list_usernames(self):
        s = TestablePlainStore(self.plain_data, "path/to/file",
                plain.PlainFileFormat)
        self.assertEqual(["alice", "bob"], list(sorted(s.usernames())))

    def test_plain_set_password(self):
        s = TestablePlainStore(self.plain_data, "path/to/files",
                plain.PlainFileFormat)
        self.assertTrue(s.authenticate("bob", "b0b"))
        s.set_password("bob", "blurb")
        self.assertFalse(s.authenticate("bob", "b0b"))
        self.assertTrue(s.authenticate("bob", "blurb"))

    def test_plain_set_password_invalid_user(self):
        s = TestablePlainStore(self.plain_data, "path/to/files",
                plain.PlainFileFormat)
        self.assertFalse(s.has_user("peter"))
        with self.assertRaises(KeyError):
            s.set_password("peter", "parker")

    def test_crypt_set_password(self):
        m = plain._crypt_methods.get("crypt", None)
        if m is None:
            self.skipTest("Crypt method 'crypt' is not supported by this"
                " Python version")
            return

        s = TestablePlainStore(self.crypt_data, "path/to/file",
                plain.HtpasswdFileFormat, m)
        s.set_password("alice", "shiny")
        self.assertFalse(s.authenticate("alice", "mirror"))
        self.assertTrue(s.authenticate("alice", "shiny"))

    def test_create_user(self):
        s = TestablePlainStore(self.plain_data, "path/to/file",
                plain.PlainFileFormat)
        s.create_user("peter", "p3t3r")
        self.assertTrue(s.has_user("peter"))
        self.assertTrue(s.authenticate("peter", "p3t3r"))

    def test_delete_user(self):
        s = TestablePlainStore(self.plain_data, "path/to/file",
                plain.PlainFileFormat)
        s.delete_user("bob")
        self.assertFalse(s.has_user("bob"))

    def test_delete_nonexisting_user(self):
        s = TestablePlainStore(self.plain_data, "path/to/file",
                plain.PlainFileFormat)
        with self.assertRaises(KeyError):
            s.delete_user("peter")

    def test_create_existing_user(self):
        s = TestablePlainStore(self.plain_data, "path/to/file",
                plain.PlainFileFormat)
        with self.assertRaises(KeyError):
            s.create_user("bob", "b0b")

    def test_create_user_with_extrainfo(self):
        s = TestablePlainStore("", "path/to/file",
                plain.PlainFileFormat)
        s.create_user("bob", "b0b", role="manager")
        self.assertTrue(s.last_io.data.startswith("bob:b0b:"))


NOT_A_FILE = "/tmp/this/is/a/very/long/path/to/a/nonexistent/file"

class TestPlainStoreOpen(unittest.TestCase):
    def test_open_nonexistent_file(self):
        s = plain.from_config({ "path": NOT_A_FILE })
        self.assertEqual([], list(s.usernames()))
