import json
from typing import Final

import xbmc

import resources.lib.exporter as exporter
import resources.lib.jsonrpc as jsonrpc
import resources.lib.utcdt as utcdt
from resources.lib.addon import addon, player
from resources.lib.settings import triggers, avoidance, periodic, ui, state
from resources.lib.sync import Sync


class Alarm:
    def __init__(self, name: str, command: str, loop: bool = False):
        self._name: Final = f'{addon.id}.{name}'
        self._command: Final = command
        self._loop: Final = ',loop' if loop else ''

        self._minutes = 0

    @property
    def is_active(self) -> bool:
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

        addon.set_logging(verbose=ui.is_logging_verbose)
        addon.set_notifications(notify=ui.should_show_notifications)

        self._active_sync = None
        self._waiting_sync = None

        self._periodic_trigger = Alarm(
            name='periodic.trigger',
            command=f'NotifyAll({addon.id},{jsonrpc.INTERNAL_METHODS.patient_sync.send})',
            loop=True
        )
        self._waiter = Alarm(
            name='avoidance.wait',
            command=f'NotifyAll({addon.id},{jsonrpc.INTERNAL_METHODS.wait_done.send})'
        )

        # If the last scan time has never been set, we'll need to set it
        if state.last_refresh is None:
            state.last_refresh = utcdt.now()

        if triggers.should_sync_on_start:
            sync, done = Sync.start()
            if not done:
                self._active_sync = sync

        self._periodic_trigger.set(periodic.period)

        while not self.abortRequested():
            self.waitForAbort(300)

    def onNotification(self, sender: str, method: str, data: str) -> None:
        if self._active_sync and method == self._active_sync.awaiting:
            self._continue_sync()

        elif method == jsonrpc.INTERNAL_METHODS.immediate_sync.recv:
            self._immediate_sync()

        elif method == jsonrpc.INTERNAL_METHODS.patient_sync.recv:
            self._patient_sync()

        elif method == jsonrpc.INTERNAL_METHODS.wait_done.recv:
            self._wait_done()

        elif method == 'Player.OnPlay':
            self._waiter.cancel()

        elif method == 'Player.OnStop':
            self._play_stop()

        elif method == 'VideoLibrary.OnUpdate' and triggers.should_export_on_update:
            self._library_update(data)

    def onSettingsChanged(self) -> None:
        addon.set_logging(verbose=ui.is_logging_verbose)
        addon.set_notifications(notify=ui.should_show_notifications)

        if self._periodic_trigger.minutes != periodic.period:
            self._periodic_trigger.set(periodic.period)

        if self._waiter.is_active and self._waiter.minutes != avoidance.wait_time:
            self._waiter.set(avoidance.wait_time)

        if (self._waiting_sync and (not avoidance.is_enabled
                                    or not avoidance.wait_time and not player.isPlaying())):
            self._wait_done()

    def _continue_sync(self) -> None:
        done = self._active_sync.resume()
        if done:
            self._active_sync = None

    def _immediate_sync(self) -> None:
        if not self._active_sync:
            sync, done = Sync.start()
            if not done:
                self._active_sync = sync

    def _library_update(self, data: str) -> None:
        data = json.loads(data)

        # Always ignore added items if they aren't part a transaction because
        # refreshing an item will trigger a non-transactional update event.
        if data.get('added') and (triggers.ignores_add_updates or not data.get('transaction')):
            return

        item = data['item']
        if item['type'] in ['movie', 'tvshow', 'episode']:
            exporter.export(item['type'], item['id'])

    def _patient_sync(self) -> None:
        if self._active_sync:
            return
        if (avoidance.is_enabled and player.isPlaying()
                or self._waiter.is_active):
            self._waiting_sync = Sync()
        else:
            self._immediate_sync()

    def _play_stop(self):
        if avoidance.wait_time:
            self._waiter.set(avoidance.wait_time)
        elif self._waiting_sync:
            self._wait_done()

    def _wait_done(self) -> None:
        self._waiter.cancel()
        self._immediate_sync()
        self._waiting_sync = None


if __name__ == "__main__":
    Service()
