import xbmcgui

from helpers import *


def refresh():
    response = jsonrpc("VideoLibrary.GetTVShows", properties=["file"])
    xbmcgui.Dialog().ok("Test", str(response))
