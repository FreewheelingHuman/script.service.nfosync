from typing import Final

import xbmc
import xbmcaddon


class _Addon(xbmcaddon.Addon):
    def __init__(self):
        super().__init__()
        self._id = self.getAddonInfo('id')
        self._name = self.getAddonInfo('name')

    @property
    def id(self) -> str:
        return self._id

    @property
    def name(self) -> str:
        return self._name

    @property
    def json_name(self) -> str:
        return self._name.replace(' ', '')

    def log(self, message: str) -> None:
        xbmc.log(f'{self._name}: {message}')


ADDON: Final = _Addon()
PLAYER: Final = xbmc.Player()