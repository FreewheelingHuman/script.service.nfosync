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
            self._importer, still_running = Importer.start(
                visible=SETTINGS.start.visible,
                clean=SETTINGS.start.clean,
                refresh=SETTINGS.start.refresh,
                scan=SETTINGS.start.scan
            )
            if not still_running:
                self._importer = None

        while not self.abortRequested():
            self.waitForAbort(100)

    def onNotification(self, sender: str, method: str, data: str) -> None:
        if self._importer and method == self._importer.awaiting:
            still_running = self._importer.resume()
            if not still_running:
                self._importer = None
            return

        if not self._importer and method == jsonrpc.custom_methods.refresh.recv:
            options = json.loads(data)
            self._importer, still_running = Importer.start(
                visible=options['visible'],
                clean=options['clean'],
                refresh=options['refresh'],
                scan=options['scan'])
            if not still_running:
                self._importer = None
            return


if __name__ == "__main__":
    Service()
