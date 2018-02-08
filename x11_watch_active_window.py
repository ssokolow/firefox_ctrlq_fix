#!/usr/bin/env python
"""Proof of concept for blocking Ctrl+Q from Firefox windows.

(Works by using XGrabKey to claim Ctrl+Q on all Firefox windows, either at
 startup or when the window first receives focus.)

Requires:
- Python
- python-xlib

Tested with Python 2.x because my Kubuntu 14.04 doesn't come with python-xlib
for Python 3.x.
"""

from __future__ import print_function

from contextlib import contextmanager
from itertools import chain, combinations
import Xlib, Xlib.display
from Xlib import X, XK

__author__ = "Stephan Sokolow (deitarion/SSokolow)"
__license__ = "MIT"

KEY = ("q", X.ControlMask)
FIREFOX_WINCLASS = "Firefox"

# Connect to the X server and get the root window
disp = Xlib.display.Display()
root = disp.screen().root

# Prepare the property names we use so they can be fed into X11 APIs
NET_ACTIVE_WINDOW = disp.intern_atom('_NET_ACTIVE_WINDOW')
NET_CLIENT_LIST = disp.intern_atom('_NET_CLIENT_LIST')

KEYSYM = XK.string_to_keysym(KEY[0])
KEYCODE = disp.keysym_to_keycode(KEYSYM)

last_seen = {'xid': None}

def vary_modmask(modmask, ignored_list):
    """Produce all combinations of modifiers which must be grabbed to
    effectively ignore the state of certain modifiers.
    """
    for ignored in chain.from_iterable(combinations(ignored_list, j)
                                       for j in range(len(ignored_list) + 1)):
        imask = reduce(lambda x, y: x | y, ignored, 0)
        yield modmask | imask

@contextmanager
def window_obj(win_id):
    """Simplify dealing with BadWindow (make it either valid or None)"""
    window_obj = None
    if win_id:
        try:
            window_obj = disp.create_resource_object('window', win_id)
        except Xlib.error.XError:
            pass
    yield window_obj

def grab_key(window):
    """Grab the undesirable key on the given Windows if it's Firefox"""
    if not window:
        return  # Allow null windows here for robustness and simple structure

    winclass = window.get_wm_class()
    if not (winclass and winclass[-1] == FIREFOX_WINCLASS):
        return  # Skip non-Firefox windows

    # To avoid the risk of an XID collision allowing data loss via Ctrl+Q,
    # take advantage of the X server not complaining if we re-grab something
    # we already grabbed.
    #
    # (In my stress tests, re-grabbing like this appears to not have any
    #  harmful consequences as long as the X11 event queue is allowed to
    #  flush properly.)
    for modmask in vary_modmask(KEY[1], (X.Mod2Mask, X.LockMask)):
        window.grab_key(KEYCODE, modmask, 1,
                        X.GrabModeAsync, X.GrabModeAsync)

def handle_xevent(event):
    """Handler for X events which aims for minimal overhead"""
    # Ignore any unwanted events as quickly and efficiently as possible in
    # concert with setting event_mask.
    if event.type != Xlib.X.PropertyNotify or event.atom != NET_ACTIVE_WINDOW:
        return

    win_id = root.get_full_property(NET_ACTIVE_WINDOW,
                                    Xlib.X.AnyPropertyType).value[0]
    if win_id == last_seen['xid']:
        return  # Active window has not changed

    last_seen['xid'] = win_id
    with window_obj(win_id) as new_win:
        grab_key(new_win)

if __name__ == '__main__':
    # Listen for _NET_ACTIVE_WINDOW changes
    root.change_attributes(event_mask=Xlib.X.PropertyChangeMask)

    # Bind existing windows (eg. in case Firefox is already focused)
    for xid in root.get_full_property(
            NET_CLIENT_LIST, X.AnyPropertyType).value:
        with window_obj(xid) as new_win:
            grab_key(new_win)

    while True:  # next_event() sleeps until we get an event
        handle_xevent(disp.next_event())
