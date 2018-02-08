#!/usr/bin/env python
"""Proof of concept for blocking Ctrl+Q from Firefox windows.

(Works by using XGrabKey to claim Ctrl+Q on all Firefox windows, either at
 startup or when the window first receives focus.)

Requires:
- Python
- python-xlib

Tested with Python 2.x because my Kubuntu 14.04 doesn't come with python-xlib
for Python 3.x.

Copyright 2018 Stephan Sokolow

Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the "Software"), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
"""

from __future__ import print_function

import time
from contextlib import contextmanager
from itertools import chain, combinations

import Xlib, Xlib.display
from Xlib import X, XK

__author__ = "Stephan Sokolow (deitarion/SSokolow)"
__license__ = "MIT"

KEY = ("q", X.ControlMask)
FIREFOX_WINCLASS = "Firefox"


def vary_modmask(modmask, ignored_list):
    """Produce all combinations of modifiers which must be grabbed to
    effectively ignore the state of certain modifiers.
    """
    for ignored in chain.from_iterable(combinations(ignored_list, j)
                                       for j in range(len(ignored_list) + 1)):
        imask = reduce(lambda x, y: x | y, ignored, 0)
        yield modmask | imask

@contextmanager
def window_obj(win_id, display):
    """Simplify dealing with BadWindow (make it either valid or None)"""
    window_obj = None
    if win_id:
        try:
            window_obj = display.create_resource_object('window', win_id)
        except Xlib.error.XError:
            pass
    yield window_obj

class KeyBlocker(object):  # pylint: disable=too-many-instance-attributes
    """Encapsulation of the program to allow reconnect on failure"""
    last_seen = None

    def __init__(self, key=KEY, winclass=FIREFOX_WINCLASS):
        self.key = key
        self.winclass = winclass

        # Connect to the X server and get the root window
        self.disp = Xlib.display.Display()
        self.root = self.disp.screen().root

        self.keysym = XK.string_to_keysym(self.key[0])
        self.keycode = self.disp.keysym_to_keycode(self.keysym)

        # Prepare the property names we use so they can be fed into X11 APIs
        self.net_active_window = self.disp.intern_atom('_NET_ACTIVE_WINDOW')
        self.net_client_list = self.disp.intern_atom('_NET_CLIENT_LIST')

        # Listen for _NET_ACTIVE_WINDOW changes
        self.root.change_attributes(event_mask=Xlib.X.PropertyChangeMask)

    def _bind_existing_windows(self):
        """Minimize the chance of a window receiving Ctrl+C before focus

        (eg. A Firefox window that was focused before we started)
        """
        for xid in self.root.get_full_property(
                self.net_client_list, X.AnyPropertyType).value:
            with window_obj(xid, self.disp) as new_win:
                self.grab_key(new_win)

    def grab_key(self, window):
        """Grab the undesirable key on the given Windows if it's Firefox"""
        if not window:
            return  # Allow null windows for robustness and simple structure

        winclass = window.get_wm_class()
        if not (winclass and winclass[-1] == self.winclass):
            return  # Skip non-Firefox windows

        # To avoid the risk of an XID collision allowing data loss via Ctrl+Q,
        # take advantage of the X server not complaining if we re-grab
        # something we already grabbed.
        #
        # (In my stress tests, re-grabbing like this appears to not have any
        #  harmful consequences as long as the X11 event queue is allowed to
        #  flush properly.)
        for modmask in vary_modmask(self.key[1], (X.Mod2Mask, X.LockMask)):
            window.grab_key(self.keycode, modmask, 1,
                            X.GrabModeAsync, X.GrabModeAsync)

    def handle_xevent(self, event):
        """Handler for X events which aims for minimal overhead"""
        # Ignore any unwanted events as quickly and efficiently as possible in
        # concert with setting event_mask.
        if (event.type != Xlib.X.PropertyNotify or
                event.atom != self.net_active_window):
            return

        win_id = self.root.get_full_property(self.net_active_window,
                                             Xlib.X.AnyPropertyType).value[0]
        if win_id == self.last_seen:
            return  # Active window has not changed

        self.last_seen = win_id
        with window_obj(win_id, self.disp) as new_win:
            self.grab_key(new_win)

    def run(self):
        """Main loop"""
        while True:  # next_event() sleeps until we get an event
            self.handle_xevent(self.disp.next_event())

if __name__ == '__main__':
    while True:
        try:
            app = KeyBlocker()
            app.run()
        except Exception as err:  # pylint: disable=broad-except
            print("Error encountered. Restarting in 1 second.\n\t{}".format(
                  err))
            time.sleep(1)
