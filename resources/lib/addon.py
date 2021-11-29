from typing import Final

import xbmc
import xbmcaddon


class _Addon(xbmcaddon.Addon):
    def __init__(self):
        super().__init__()
        self._id: Final = self.getAddonInfo('id')
        self._name: Final = self.getAddonInfo('name')
        self._version: Final = self.getAddonInfo('version')
        self._profile: Final = self.getAddonInfo('profile')

    @property
    def id(self) -> str:
        return self._id

    @property
    def name(self) -> str:
        return self._name

    @property
    def json_name(self) -> str:
        return self._name.replace(' ', '')

    @property
    def profile(self) -> str:
        return self._profile

    @property
    def version(self) -> str:
        return self._version

    def log(self, message: str) -> None:
        xbmc.log(f'{self._name}: {message}')


ADDON: Final = _Addon()
PLAYER: Final = xbmc.Player()
