#!/usr/bin/env python
"""python-xlib example which reacts to changing the active window.

Based on my earlier example from
https://gist.github.com/ssokolow/e7c9aae63fb7973e4d64cff969a78ae8

Requires:
- Python
- python-xlib

Tested with Python 2.x because my Kubuntu 14.04 doesn't come with python-xlib
for Python 3.x.

Design:
-------

Any modern window manager that isn't horrendously broken maintains an X11
property on the root window named _NET_ACTIVE_WINDOW.

This listens for changes to it and then hides duplicate events
so it only reacts to title changes once.
"""

FIREFOX_WINCLASS = "Firefox"

from contextlib import contextmanager
import Xlib
from Xlib import X, display

# Connect to the X server and get the root window
disp = Xlib.display.Display()
root = disp.screen().root

# Prepare the property names we use so they can be fed into X11 APIs
NET_ACTIVE_WINDOW = disp.intern_atom('_NET_ACTIVE_WINDOW')
NET_CLIENT_LIST = disp.intern_atom('_NET_CLIENT_LIST')

last_seen = {'xid': None}

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
    if not window:  # TODO: ...or already seen
        return  # Allow null windows here for robustness and simple structure

    winclass = window.get_wm_class()
    if not (winclass and winclass[-1] == FIREFOX_WINCLASS):
        return  # Skip non-Firefox windows

    print("TODO: Bind Ctrl+Q for new window if Firefox")

def handle_xevent(event):
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
