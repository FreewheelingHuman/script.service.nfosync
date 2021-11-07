import xbmcgui

from resources.lib.helpers import *


response = jsonrpc("VideoLibrary.GetTVShows", properties=["file"])

xbmcgui.Dialog().ok("Test", str(response))
