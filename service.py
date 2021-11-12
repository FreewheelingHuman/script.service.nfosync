import json
from typing import Final

import xbmc

import resources.lib.jsonrpc as jsonrpc
import resources.lib.utcdt as utcdt
from resources.lib.importer import Importer
from resources.lib.addon import ADDON_ID, SETTINGS


class Service(xbmc.Monitor):
    def __init__(self):
        super().__init__()

        self._importer = None

        self._periodic_alarm: Final = f'{ADDON_ID}.periodic_alarm'
        self._periodic_alarm_period = 0

        self._wait_alarm: Final = f'{ADDON_ID}.wait_alarm'

        # If the last scan time has never been set, we'll need to set it
        if SETTINGS.state.last_refresh is None:
            SETTINGS.state.last_refresh = utcdt.now()

        if SETTINGS.start.enabled:
            self._importer, done = Importer.start(
                visible=SETTINGS.start.visible,
                clean=SETTINGS.start.clean,
                refresh=SETTINGS.start.refresh,
                scan=SETTINGS.start.scan
            )
            if done:
                self._importer = None

        if SETTINGS.periodic.enabled:
            self._set_periodic_alarm()

        while not self.abortRequested():
            self.waitForAbort(300)

    def onNotification(self, sender: str, method: str, data: str) -> None:
        if self._importer and method == self._importer.awaiting:
            done = self._importer.resume()
            if done:
                self._importer = None
            return

        if not self._importer and method == jsonrpc.custom_methods.import_now.recv:
            options = json.loads(data)
            self._importer, done = Importer.start(
                visible=options['visible'],
                clean=options['clean'],
                refresh=options['refresh'],
                scan=options['scan'])
            if done:
                self._importer = None
            return

    def onSettingsChanged(self) -> None:
        # Reset the periodic alarm if it is toggled or the period is changed
        if SETTINGS.periodic.enabled and not self._periodic_alarm_period:
            self._set_periodic_alarm()
        elif not SETTINGS.periodic.enabled and self._periodic_alarm_period:
            self._cancel_periodic_alarm()
        elif self._periodic_alarm_period != SETTINGS.periodic.period:
            self._set_periodic_alarm()

    def _set_periodic_alarm(self) -> None:
        if self._periodic_alarm_period:
            self._cancel_periodic_alarm()

        settings = json.dumps({
            'visible': SETTINGS.periodic.visible,
            'clean': SETTINGS.periodic.clean,
            'refresh': SETTINGS.periodic.refresh,
            'scan': SETTINGS.periodic.scan
        })
        command = f'NotifyAll({ADDON_ID},{jsonrpc.custom_methods.import_wait.send},"{settings}")'
        time = str(SETTINGS.periodic.period) + ':00:00'
        xbmc.executebuiltin(f'AlarmClock({self._periodic_alarm},{command},{time},silent,loop)')

        self._periodic_alarm_period = SETTINGS.periodic.period

    def _cancel_periodic_alarm(self) -> None:
        xbmc.executebuiltin(f'CancelAlarm({self._periodic_alarm}, silent)')
        self._periodic_alarm_period = 0


if __name__ == "__main__":
    Service()
