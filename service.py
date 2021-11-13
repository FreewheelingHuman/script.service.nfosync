import collections
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

        self._import_queue = collections.deque()
        self._periodic_wait_queue = collections.deque()

        self._periodic_trigger_alarm: Final = f'{ADDON_ID}.periodic_alarm'
        self._periodic_trigger_alarm_length = 0
        self._periodic_wait_alarm: Final = f'{ADDON_ID}.periodic_wait_alarm'
        self._periodic_wait_alarm_running = False

        # If the last scan time has never been set, we'll need to set it
        if SETTINGS.state.last_refresh is None:
            SETTINGS.state.last_refresh = utcdt.now()

        if SETTINGS.start.enabled:
            importer, done = Importer.start(
                visible=SETTINGS.start.visible,
                clean=SETTINGS.start.clean,
                refresh=SETTINGS.start.refresh,
                scan=SETTINGS.start.scan
            )
            if not done:
                self._import_queue.append(importer)

        if SETTINGS.periodic.enabled:
            self._set_periodic_trigger_alarm()

        while not self.abortRequested():
            self.waitForAbort(300)

    def onNotification(self, sender: str, method: str, data: str) -> None:
        if self._import_queue and method == self._import_queue[0].awaiting:
            while True:
                done = self._import_queue[0].resume()
                if done:
                    self._import_queue.popleft()
                    if self._import_queue:
                        continue
                break
            return

        if method == jsonrpc.custom_methods.import_now.recv:
            options = json.loads(data)
            importer = Importer(
                visible=options['visible'],
                clean=options['clean'],
                refresh=options['refresh'],
                scan=options['scan'])
            if self._import_queue:
                self._import_queue.append(importer)
            else:
                done = importer.resume()
                if not done:
                    self._import_queue.append(importer)
            return

        if method == 'Player.OnStop':
            if self._periodic_wait_queue:
                self._set_periodic_wait_alarm()
            return

    def onSettingsChanged(self) -> None:
        # Reset the periodic alarm if it is toggled or the period is changed
        if SETTINGS.periodic.enabled and not self._periodic_trigger_alarm_length:
            self._set_periodic_trigger_alarm()
        elif not SETTINGS.periodic.enabled and self._periodic_trigger_alarm_length:
            self._cancel_periodic_trigger_alarm()
        elif self._periodic_trigger_alarm_length != SETTINGS.periodic.period:
            self._set_periodic_trigger_alarm()

    def _set_periodic_trigger_alarm(self) -> None:
        if self._periodic_trigger_alarm_length:
            self._cancel_periodic_trigger_alarm()

        settings = json.dumps({
            'visible': SETTINGS.periodic.visible,
            'clean': SETTINGS.periodic.clean,
            'refresh': SETTINGS.periodic.refresh,
            'scan': SETTINGS.periodic.scan
        })
        command = f'NotifyAll({ADDON_ID},{jsonrpc.custom_methods.import_periodic.send},"{settings}")'
        time = f'{SETTINGS.periodic.period}:00:00'
        xbmc.executebuiltin(f'AlarmClock({self._periodic_trigger_alarm},{command},{time},silent,loop)')

        self._periodic_trigger_alarm_length = SETTINGS.periodic.period

    def _set_periodic_wait_alarm(self) -> None:
        if self._periodic_wait_alarm_running:
            self._cancel_periodic_wait_alarm()

        command = f'NotifyAll({ADDON_ID},{jsonrpc.custom_methods.periodic_wait_done.send})'
        time = f'{SETTINGS.periodic.waitafterplay // 60}:{SETTINGS.periodic.waitafterplay % 60}:00'
        xbmc.executebuiltin(f'AlarmClock({self._periodic_wait_alarm},{command},{time},silent)')

        self._periodic_wait_alarm_running = True

    def _cancel_periodic_trigger_alarm(self) -> None:
        xbmc.executebuiltin(f'CancelAlarm({self._periodic_trigger_alarm}, silent)')
        self._periodic_trigger_alarm_length = 0

    def _cancel_periodic_wait_alarm(self) -> None:
        xbmc.executebuiltin(f'CancelAlarm({self._periodic_wait_alarm}, silent)')
        self._periodic_wait_alarm_running = False


if __name__ == "__main__":
    Service()
