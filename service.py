import json

import xbmc

import resources.lib.jsonrpc as jsonrpc
import resources.lib.utcdt as utcdt
from resources.lib.refresher import Refresher
from resources.lib.settings import Settings


class Service(xbmc.Monitor):
    def __init__(self):
        super().__init__()

        self._settings = Settings()
        self._refresher = None

        # If the last scan time has never been set, we'll need to set it
        if self._settings.state.last_scan is None:
            self._settings.state.last_scan = utcdt.now()

        self._refresher = Refresher(clean=self._settings.start.clean, scan=self._settings.start.scan)

        while not self.abortRequested():
            self.waitForAbort(100)

    def onNotification(self, sender: str, method: str, data: str) -> None:
        if method == 'VideoLibrary.OnCleanFinished' and self._refresher_running:
            self._refresher.resume()
        elif method == jsonrpc.custom_methods.refresh.recv and not self._refresher_running:
            options = json.loads(data)
            self._refresher = Refresher(clean=options['clean'], scan=options['scan'])

    @property
    def _refresher_running(self) -> bool:
        if self._refresher is None:
            return False
        return self._refresher.running


if __name__ == "__main__":
    Service()
