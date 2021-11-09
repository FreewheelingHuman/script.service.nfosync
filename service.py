import datetime

import xbmc

from resources.lib.refresher import refresh
from resources.lib.settings import Settings


class Service(xbmc.Monitor):
    def __init__(self):
        super().__init__()

        self._settings = Settings()

        # If the last scan time has never been set, we'll need to set it
        if self._settings.state.last_scan is None:
            self._settings.state.last_scan = datetime.datetime.now()

        # Clear the in progress status so if a run didn't finish, a restart will at least fix it
        self._settings.in_progress.active = False

        refresh(clean=self._settings.start.clean)

        while not self.abortRequested():
            self.waitForAbort(100)

    def onCleanFinished(self, library):
        if library == 'video' and self._settings.in_progress.active:
            self._settings.in_progress.active = False
            refresh(clean=self._settings.in_progress.clean)


if __name__ == "__main__":
    Service()
