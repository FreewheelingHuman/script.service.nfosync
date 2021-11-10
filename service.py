import json

import xbmc

import resources.lib.jsonrpc as jsonrpc
import resources.lib.utcdt as utcdt
from resources.lib.refresher import refresh
from resources.lib.settings import Settings


class Service(xbmc.Monitor):
    def __init__(self):
        super().__init__()

        self._settings = Settings()

        # If the last scan time has never been set, we'll need to set it
        if self._settings.state.last_scan is None:
            self._settings.state.last_scan = utcdt.now()

        # Clear the in progress status so if a run didn't finish, a restart will at least fix it
        self._settings.in_progress.active = False

        refresh(clean=self._settings.start.clean, scan=self._settings.start.scan)

        while not self.abortRequested():
            self.waitForAbort(100)

    def onCleanFinished(self, library: str) -> None:
        if library == 'video' and self._settings.in_progress.active:
            refresh(clean=self._settings.in_progress.clean, scan=self._settings.in_progress.scan, continuation=True)

    def onNotification(self, sender: str, method: str, data: str) -> None:
        if sender == self._settings.addon_id and method == jsonrpc.custom_methods.refresh.recv:
            options = json.loads(data)
            refresh(clean=options['clean'], scan=options['scan'])


if __name__ == "__main__":
    Service()
