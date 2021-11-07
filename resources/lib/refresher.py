import xbmcgui

from resources.lib.helpers import *


def refresh():
    response = jsonrpc("VideoLibrary.GetTVShows", properties=["file"])
    response = jsonrpc("VideoLibrary.RefreshTVShow", tvshowid=response["tvshows"][0]["tvshowid"])
    xbmcgui.Dialog().ok("Test", str(response))
