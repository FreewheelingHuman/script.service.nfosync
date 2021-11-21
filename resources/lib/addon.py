from typing import Final

import xbmc
import xbmcaddon


ADDON: Final = xbmcaddon.Addon()
ADDON_ID: Final = ADDON.getAddonInfo('id')
PLAYER: Final = xbmc.Player()
