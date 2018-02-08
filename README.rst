==================
Firefox Ctrl+Q Fix
==================

A simple utility for X11-based desktops to work around `Bug 1325692`_ which
currently prevents the `Disable Ctrl-Q and Cmd-Q`_ extension for Firefox from working on Linux.

My intent is to rewrite this in Rust to minimize the resource overhead and
experiment with how self-contained I can get it but, since the proof of concept
I wrote in Python works, I might as well share it now.

.. _Bug 1325692: https://bugzilla.mozilla.org/show_bug.cgi?id=1325692
.. _Disable Ctrl-Q and Cmd-Q: https://addons.mozilla.org/en-US/firefox/addon/disable-ctrl-q-and-cmd-q/

Requirements
============

* Python 2.7
* ``python-xlib``

Usage
=====

Run the ``firefox_ctrlq_fix.py`` script in the background.

Mechanism
=========

The script finds Firefox windows in two ways:

1. When first started, it queries ``_NET_CLIENT_LIST`` for a list of top-level
   application windows and then filters for ones with a ``WM_CLASS`` of
   ``Firefox``.

2. It registers itself to be notified when the ``_NET_ACTIVE_WINDOW`` property
   on the root window changes, then checks whether the newly focused window
   has ``Firefox`` as its ``WM_CLASS``.

(I tested this as working to match both Firefox 52.6.0 ESR and Firefox Developer
Edition 59.0b7 but haven't tested it against the unbranded builds.)

The script blocks ``Ctrl+Q`` by calling ``XGrabKey`` on each Firefox window it
finds for all four possible states that the Num Lock and Caps Lock keys may be
in, and then ignoring the events it receives.

(Num Lock and Caps Lock are modifiers in the same way Ctrl, Alt, and Shift
are, so Ctrl+NumLock+Q is a different key combo than Ctrl+Q at the level X11
operates at, but programs like Firefox ignore the state of locking modifiers.)

At the moment, it does no "have I seen this window before?" checking for three
reasons:

1. I've heard of XID collisions occurring in the wild (`example <https://bugs.launchpad.net/ubuntu/+source/firefox-3.5/+bug/401823>`_), and I don't want to
   leave a Firefox Window with ``Ctrl+Q`` functional because my script got
   confused about whether it has seen it before.

2. Aside from doing extra work, there seems to be no harm to calling
   ``XGrabKey`` multiple times on the same window. (I did a stress test where I
   spammed the X server with thousands of identical ``XGrabKey`` requests per
   second for several minutes while I went to make some tea.)

3. I didn't want to reinvent part of the X server that apparently already
   exists within the ``XGrabKey`` implementation.
