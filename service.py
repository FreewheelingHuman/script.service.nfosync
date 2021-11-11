import json

import xbmc

import resources.lib.jsonrpc as jsonrpc
import resources.lib.utcdt as utcdt
from resources.lib.importer import Importer
from resources.lib.settings import Settings


class Service(xbmc.Monitor):
    def __init__(self):
        super().__init__()

        self._settings = Settings()
        self._importer = None

        # If the last scan time has never been set, we'll need to set it
        if self._settings.state.last_refresh is None:
            self._settings.state.last_refresh = utcdt.now()

        self._importer = Importer(clean=self._settings.start.clean, scan=self._settings.start.scan)

        while not self.abortRequested():
            self.waitForAbort(100)

    def onNotification(self, sender: str, method: str, data: str) -> None:
        if method == 'VideoLibrary.OnCleanFinished' and self._refresher_running:
            self._importer.resume()
        elif method == jsonrpc.custom_methods.refresh.recv and not self._refresher_running:
            options = json.loads(data)
            self._importer = Importer(clean=options['clean'], scan=options['scan'])

    @property
    def _refresher_running(self) -> bool:
        if self._importer is None:
            return False
        return self._importer.running


if __name__ == "__main__":
    Service()
