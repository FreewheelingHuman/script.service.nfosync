import collections
import json
from typing import Final

import xbmc

import resources.lib.exporter as exporter
import resources.lib.jsonrpc as jsonrpc
import resources.lib.utcdt as utcdt
from resources.lib.importer import Importer
from resources.lib.addon import ADDON_ID, PLAYER, SETTINGS


class Alarm:
    def __init__(self, name: str, command: str, loop: bool = False):
        self._name: Final = f'{ADDON_ID}.{name}'
        self._command: Final = command
        self._loop: Final = ',loop' if loop else ''

        self._minutes = 0

    @property
    def active(self) -> bool:
        return bool(self._minutes)

    @property
    def minutes(self) -> int:
        return self._minutes

    def set(self, minutes):
        self.cancel()
        if minutes > 0:
            self._minutes = minutes
            xbmc.executebuiltin(f'AlarmClock({self._name},{self._command},{self._minutes},silent{self._loop})')

    def cancel(self):
        xbmc.executebuiltin(f'CancelAlarm({self._name},silent)')
        self._minutes = 0


class Service(xbmc.Monitor):
    def __init__(self):
        super().__init__()

        self._import_queue = collections.deque()

        self._waiting_periodic = None
        self._periodic_trigger = Alarm(
            name='periodic.trigger',
            command=f'NotifyAll({ADDON_ID},{jsonrpc.custom_methods.import_periodic.send})',
            loop=True
        )
        self._periodic_waiter = Alarm(
            name='periodic.wait',
            command=f'NotifyAll({ADDON_ID},{jsonrpc.custom_methods.periodic_wait_done.send})'
        )

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
            self._periodic_trigger.set(SETTINGS.periodic.period)

        while not self.abortRequested():
            self.waitForAbort(300)

    def onNotification(self, sender: str, method: str, data: str) -> None:
        if self._import_queue and method == self._import_queue[0].awaiting:
            self._continue_importing()

        elif method == jsonrpc.custom_methods.import_now.recv:
            self._import_now_request(data)

        elif method == jsonrpc.custom_methods.import_periodic.recv:
            self._periodic_import_request()

        elif method == jsonrpc.custom_methods.periodic_wait_done.recv:
            self._periodic_wait_done()

        elif method == 'Player.OnPlay':
            self._periodic_waiter.cancel()

        elif method == 'Player.OnStop':
            self._periodic_play_stop()

        elif method == 'VideoLibrary.OnUpdate' and SETTINGS.export.enabled:
            self._process_update(data)

    def onSettingsChanged(self) -> None:
        if self._periodic_trigger.minutes != SETTINGS.periodic.period:
            self._periodic_trigger.set(SETTINGS.periodic.period)

        if self._periodic_waiter.active and self._periodic_waiter.minutes != SETTINGS.periodic.wait:
            self._periodic_waiter.set(SETTINGS.periodic.wait)

        if (self._waiting_periodic and (not SETTINGS.periodic.avoid_play
                                        or not SETTINGS.periodic.wait and not PLAYER.isPlaying())):
            self._periodic_wait_done()

    def _periodic_play_stop(self):
        if SETTINGS.periodic.wait:
            self._periodic_waiter.set(SETTINGS.periodic.wait)
        elif self._waiting_periodic:
            self._periodic_wait_done()

    def _import_now_request(self, data) -> None:
        options = json.loads(data)
        importer = Importer(
            visible=options['visible'],
            clean=options['clean'],
            refresh=options['refresh'],
            scan=options['scan'])
        self._import_soon(importer)

    def _periodic_import_request(self) -> None:
        importer = Importer(
            visible=SETTINGS.periodic.visible,
            clean=SETTINGS.periodic.clean,
            refresh=SETTINGS.periodic.refresh,
            scan=SETTINGS.periodic.scan
        )
        if (SETTINGS.periodic.avoid_play and PLAYER.isPlaying()
                or self._periodic_waiter.active):
            self._waiting_periodic = importer
        else:
            self._import_soon(importer)

    def _periodic_wait_done(self) -> None:
        self._periodic_waiter.cancel()
        self._import_soon(self._waiting_periodic)
        self._waiting_periodic = None

    def _continue_importing(self) -> None:
        while True:
            done = self._import_queue[0].resume()
            if done:
                self._import_queue.popleft()
                if self._import_queue:
                    continue
            break

    def _import_soon(self, importer: Importer) -> None:
        if self._import_queue:
            self._import_queue.append(importer)
        else:
            done = importer.resume()
            if not done:
                self._import_queue.append(importer)

    @staticmethod
    def _process_update(data: str) -> None:
        data = json.loads(data)

        # Ignore freshly added items - they don't need to be exported
        if data.get('added'):
            return

        item = data['item']
        if item['type'] in ['movie', 'tvshow', 'episode']:
            exporter.export(item['id'])


if __name__ == "__main__":
    Service()
