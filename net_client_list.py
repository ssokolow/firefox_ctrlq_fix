"""Proof of concept for querying a list of top-level Firefox windows"""

import Xlib
from Xlib.display import Display

display = Display()
root = display.screen().root

NET_CLIENT_LIST = display.intern_atom('_NET_CLIENT_LIST')

for xid in root.get_full_property(
        NET_CLIENT_LIST, Xlib.X.AnyPropertyType).value:
    window = display.create_resource_object('window', xid)
    winclass = window.get_wm_class()
    if winclass and winclass[-1].lower() == 'firefox':
        print("{} is {}".format(xid, winclass))
