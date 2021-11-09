import xbmcaddon

from resources.lib.refresher import refresh


addon = xbmcaddon.Addon()
clean = addon.getSettingBool('manual.clean')

refresh(clean=clean)
