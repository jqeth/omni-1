===============
 Configuration
===============

OMNI is configured using a text-based configuration file which is typically
located at ``/etc/omni.conf``. The configuration file is read using the
`wcfg <https://github.com/aperezdc/python-wcfg>`__ module, so it uses the
same basic syntax as recognized by it.


Stores
======

Each source that can provide OMNI with a method to authenticate users and
information about them is a *store*. Multiple stores can be defined in the
configuration, and any number of stores can be grouped under a `realm
<realms_>`__. Stores can be used for authentication themselves, too.


Plain Text
----------
.. automodule:: omni.stores.plain

PAM
---
.. automodule:: omni.stores.pam

Trivial
-------
.. automodule:: omni.stores.trivial


Realms
======

A *realm* is a collection of stores_. Authentication and authorization are
typically performed by using a realm. When checking credentials, a realm will
try each one of the methods from the ``method`` list, in order. It is enough
for one of the methods to succeed; otherwise access is denied if all the
methods fail to grant access. Any number of realms can be defined, and an
optional description can be attached to them:

.. literalinclude:: ../examples/trivial-and-pam.conf
   :language: lighttpd
   :linenos:
