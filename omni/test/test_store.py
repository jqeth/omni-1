#! /usr/bin/env python
# -*- coding: utf-8 -*-
# vim:fenc=utf-8
#
# Copyright © 2014 Adrian Perez <aperez@igalia.com>
#
# Distributed under terms of the MIT license.

import unittest
from .. import store


class TestAuthenticator(unittest.TestCase):

    def setUp(self):
        self.a = store.Authenticator()

    def test_authenticator_authenticate(self):
        with self.assertRaises(NotImplementedError):
            self.a.authenticate("bob", "b0b")

    def test_authenticator_usernames(self):
        with self.assertRaises(NotImplementedError):
            l = list(self.a.usernames())

    def test_authenticator_set_password(self):
        with self.assertRaises(NotImplementedError):
            self.a.set_password("bob", "b0b")

    def test_authenticator_has_user(self):
        with self.assertRaises(NotImplementedError):
            e = self.a.has_user("bob")

    def test_authenticator_get_user(self):
        with self.assertRaises(NotImplementedError):
            u = self.a.get_user("bob")

    def test_authenticator_create_user(self):
        with self.assertRaises(NotImplementedError):
            self.a.create_user("bob", "b0b")

    def test_authenticator_delete_user(self):
        with self.assertRaises(NotImplementedError):
            self.a.delete_user("bob")


class _RealmBaseTest(object):

    def test_realm_authenticate(self):
        with self.assertRaises(KeyError):
            self.r.authenticate("bob", "b0b")

    def test_realm_usernames(self):
        self.assertEquals([], list(self.r.usernames()))

    def test_realm_set_password(self):
        with self.assertRaises(KeyError):
            self.r.set_password("bob", "b0b")

    def test_realm_has_user(self):
        self.assertFalse(self.r.has_user("bob"))

    def test_realm_get_user(self):
        with self.assertRaises(KeyError):
            u = self.r.get_user("bob")

    def test_realm_create_user(self):
        with self.assertRaises(NotImplementedError):
            self.r.create_user("bob", "b0b")

    def test_realm_delete_user(self):
        with self.assertRaises(NotImplementedError):
            self.r.delete_user("bob")

    def test_realm_is_readonly(self):
        self.assertTrue(self.r.readonly)


class TestEmptyRealm(unittest.TestCase, _RealmBaseTest):
    def setUp(self):
        self.r = store.Realm("test realm")


class DummyStore(store.Base):
    def authenticate(self, username, password):
        raise KeyError(username)

    def usernames(self):
        return ()

    def set_password(self, username, password):
        raise KeyError(username)

    def has_user(self, username):
        return False

    def get_user(self, username):
        raise KeyError(username)


class WritableDummyStore(DummyStore):
    readonly = False


class TestRealmWithEmptyAuthenticator(unittest.TestCase, _RealmBaseTest):
    def setUp(self):
        self.r = store.Realm("test realm", DummyStore())


class TestRealmWithEmptyWritableAuthenticators(unittest.TestCase,
        _RealmBaseTest):
    def setUp(self):
        self.r = store.Realm("test realm", DummyStore(),
                WritableDummyStore())

    def test_realm_is_readonly(self):
        self.assertFalse(self.r.readonly)


class TestRealm(unittest.TestCase):
    def setUp(self):
        from ..stores import trivial
        self.r = store.Realm("trivial realm",
                trivial.TrivialStore("bob", "b0b"),
                trivial.TrivialStore("alice", "al1ce"))

    def test_authenticate_valid(self):
        self.assertTrue(self.r.authenticate("bob", "b0b"))
        self.assertTrue(self.r.authenticate("alice", "al1ce"))

    def test_authenticate_invalid(self):
        self.assertFalse(self.r.authenticate("bob", "b"))
        self.assertFalse(self.r.authenticate("alice", "a"))

    def test_authenticate_nonexistent(self):
        with self.assertRaises(KeyError):
            self.r.authenticate("kenny", "g")

    def test_usernames(self):
        self.assertEqual(["alice", "bob"], list(sorted(self.r.usernames())))

    def test_set_password(self):
        self.r.set_password("bob", "blurb")
        self.assertTrue(self.r.authenticate("bob", "blurb"))
        self.assertFalse(self.r.authenticate("bob", "b0b"))
        self.r.set_password("alice", "blarb")
        self.assertTrue(self.r.authenticate("alice", "blarb"))
        self.assertFalse(self.r.authenticate("alice", "al1ce"))

    def test_set_password_nonexistent(self):
        with self.assertRaises(KeyError):
            self.r.set_password("kenny", "g")

    def test_has_user(self):
        self.assertTrue(self.r.has_user("bob"))
        self.assertTrue(self.r.has_user("alice"))
        self.assertFalse(self.r.has_user("kenny"))

    def test_get_user(self):
        # FIXME: Change when stores implement getting user details.
        with self.assertRaises(NotImplementedError):
            u = self.r.get_user("bob")
        with self.assertRaises(NotImplementedError):
            u = self.r.get_user("alice")

    def test_get_user_nonexistent(self):
        with self.assertRaises(KeyError):
            u = self.r.get_user("kenny")

    def test_is_readonly(self):
        self.assertFalse(self.r.readonly)

    def test_create_user(self):
        with self.assertRaises(NotImplementedError):
            self.r.create_user("bob", "b0b")


class TestRealmDupUsers(TestRealm):
    def setUp(self):
        from ..stores import trivial
        self.r = store.Realm("trivial realm",
                trivial.TrivialStore("bob", "b0b"),
                trivial.TrivialStore("alice", "al1ce"),
                trivial.TrivialStore("alice", "al1ce2"))


class TestReadonlyStore(TestRealm):
    def setUp(self):
        super(TestReadonlyStore, self).setUp()
        for s in self.r:
            s.readonly = True

    def test_set_password(self):
        with self.assertRaises(store.AccessError):
            self.r.set_password("bob", "blurb")

    def test_is_readonly(self):
        self.assertTrue(self.r.readonly)


class TestOMNI(unittest.TestCase):
    def setUp(self):
        self.o = store.OMNI()

    def test_add_store(self):
        s = DummyStore()
        self.o.add_store("dummy.store", s)
        self.assertEqual(s, self.o.get_store("dummy.store"))

    def test_add_realm_and_store(self):
        s = DummyStore()
        self.o.add_store("dummy.store", s)
        r = store.Realm("default realm", s)

        self.o.add_realm("default", r)
        self.assertEqual(r, self.o.get_realm("default"))
        self.assertEqual(r, self.o["default"])
        self.assertTrue("default" in self.o)

        self.assertEqual(r, self.o.get_realm_or_store("default"))
        self.assertEqual(s, self.o.get_realm_or_store("dummy.store"))

    def test_add_store_duplicate(self):
        s = DummyStore()
        self.o.add_store("dummy.store", s)
        with self.assertRaises(KeyError):
            self.o.add_store("dummy.store", s)

    def test_add_realm_duplicate(self):
        s = DummyStore()
        self.o.add_store("dummy.store", s)
        r = store.Realm("default realm", s)
        self.o.add_realm("default", r)
        with self.assertRaises(KeyError):
            self.o.add_realm("default", r)

    def test_enumerate_stores(self):
        self.assertEqual([], list(self.o.stores))
        s = DummyStore()
        self.o.add_store("dummy.store", s)
        self.assertEqual([("dummy.store", s)], list(self.o.stores))

    def test_enumerate_realms(self):
        self.assertEqual([], list(self.o.realms))
        s = DummyStore()
        self.o.add_store("dummy.store", s)
        r = store.Realm("default realm", s)
        self.o.add_realm("default", r)
        self.assertEqual([("default", r)], list(self.o.realms))
