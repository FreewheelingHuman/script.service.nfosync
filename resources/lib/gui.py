from typing import Final

import xbmcgui

import resources.lib.settings as settings
from resources.lib.addon import addon


_foreground_progress: Final = xbmcgui.DialogProgress()
_background_progress: Final = xbmcgui.DialogProgressBG()


class _Progress:

    def __init__(self, heading: int):
        self._dialog = None
        self._heading: Final = addon.getLocalizedString(heading)
        self._active = False

    def set(self, message: int, progress: int, total: int) -> None:
        if not self._active:
            self._dialog.create(self._heading)
            self._active = True

        message = addon.getLocalizedString(message)
        percent = int(progress / total * 100)
        self._dialog.update(percent, message)

    def close(self) -> None:
        if not self._active:
            return
        self._dialog.close()
        self._active = False


class SyncProgress(_Progress):

    def __init__(self):
        super().__init__(32011)
        self._dialog: Final = _background_progress

    def set(self, message: int, progress: int, total: int) -> None:
        if self._active or settings.ui.should_show_sync:
            super().set(message, progress, total)


class AllActionProgress(_Progress):

    def __init__(self, heading: int):
        super().__init__(heading)
        self._dialog: Final = _foreground_progress

    @property
    def is_canceled(self) -> bool:
        if self._active:
            return self._dialog.iscanceled()
        return False
