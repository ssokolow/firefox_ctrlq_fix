"""Proof of concept for querying a list of top-level Firefox windows"""

from __future__ import print_function

from itertools import chain, combinations
from Xlib import X, XK
from Xlib.display import Display

def vary_modmask(modmask, ignored_list):
    """Produce all combinations of modifiers which must be grabbed to
    effectively ignore the state of certain modifiers.
    """
    for ignored in chain.from_iterable(combinations(ignored_list, j)
                                       for j in range(len(ignored_list) + 1)):
        imask = reduce(lambda x, y: x | y, ignored, 0)
        print(imask)
        yield modmask | imask

display = Display()
root = display.screen().root
root.change_attributes(event_mask=X.KeyPressMask | X.KeyReleaseMask)

NET_CLIENT_LIST = display.intern_atom('_NET_CLIENT_LIST')
key = "q"
keysym = XK.string_to_keysym(key)
keycode = display.keysym_to_keycode(keysym)
mask = X.ControlMask
window_class = "Firefox"

for xid in root.get_full_property(
        NET_CLIENT_LIST, X.AnyPropertyType).value:
    window = display.create_resource_object('window', xid)
    winclass = window.get_wm_class()
    if winclass and winclass[-1].lower() == window_class.lower():
        print("{} is {}".format(xid, winclass))
        for modmask in vary_modmask(mask, (X.Mod2Mask, X.LockMask)):
            window.grab_key(keycode, modmask, 1,
                            X.GrabModeAsync, X.GrabModeAsync)

display.sync()
while True:
    event = display.next_event()
    print("Blocked keypress to {}".format(window_class))
