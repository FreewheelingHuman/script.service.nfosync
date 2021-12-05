from typing import Final, Optional

import xbmc
import xbmcaddon
import xbmcgui


class _Addon(xbmcaddon.Addon):
    def __init__(self):
        super().__init__()

        self._dialog = xbmcgui.Dialog()

        self._id: Final = self.getAddonInfo('id')
        self._name: Final = self.getAddonInfo('name')
        self._version: Final = self.getAddonInfo('version')
        self._profile: Final = self.getAddonInfo('profile')

        self._verbose = True
        self._notify = True

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

    def log(self, message: str, verbose: bool = False) -> None:
        if verbose and not self._verbose:
            return
        xbmc.log(f'{self._name}: {message}')

    def set_logging(self, verbose: bool) -> None:
        self._verbose = verbose

    def notify(self, heading: str, message: str) -> None:
        if not self._notify:
            return
        self._dialog.notification(heading, message, xbmcgui.NOTIFICATION_ERROR)

    def set_notifications(self, notify: bool) -> None:
        self._notify = notify


ADDON: Final = _Addon()
PLAYER: Final = xbmc.Player()
