import datetime

import xbmc
import xbmcaddon

from resources.lib.refresher import refresh


class Service(xbmc.Monitor):
    def __init__(self):
        super().__init__()

        self._addon = xbmcaddon.Addon()

        # If the last scan time has never been set, we'll need to set it
        if self._addon.getSetting('state.last_scan') == 'none':
            self._addon.setSetting(
                'state.last_scan',
                datetime.datetime.now(datetime.timezone.utc).isoformat(timespec='seconds')
            )

        # Clear the in progress status so if a run didn't finish, a restart will at least fix it
        self._addon.setSettingBool('in_progress.active', False)

        clean = self._addon.getSettingBool('on_start.clean')
        refresh(clean=clean)

        while not self.abortRequested():
            self.waitForAbort(100)

    def onCleanFinished(self, library):
        if library == 'video' and self._addon.getSettingBool('in_progress.active'):
            refresh(clean=False)


if __name__ == "__main__":
    Service()
