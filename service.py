import json

import xbmc

import resources.lib.jsonrpc as jsonrpc
import resources.lib.utcdt as utcdt
from resources.lib.importer import Importer
from resources.lib.addon import SETTINGS


class Service(xbmc.Monitor):
    def __init__(self):
        super().__init__()

        self._importer = None

        # If the last scan time has never been set, we'll need to set it
        if SETTINGS.state.last_refresh is None:
            SETTINGS.state.last_refresh = utcdt.now()

        if SETTINGS.start.enabled:
            self._importer = Importer(
                clean=SETTINGS.start.clean,
                refresh=SETTINGS.start.refresh,
                scan=SETTINGS.start.scan
            )

        while not self.abortRequested():
            self.waitForAbort(100)

    def onNotification(self, sender: str, method: str, data: str) -> None:
        if self._importer_running and method == self._importer.awaiting:
            self._importer.resume()
            return

        if not self._importer_running and method == jsonrpc.custom_methods.refresh.recv:
            options = json.loads(data)
            self._importer = Importer(
                clean=options['clean'],
                refresh=options['refresh'],
                scan=options['scan'])
            return

    @property
    def _importer_running(self) -> bool:
        if self._importer is None:
            return False
        return self._importer.running


if __name__ == "__main__":
    Service()
