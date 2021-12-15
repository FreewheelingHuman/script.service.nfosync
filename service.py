import datetime
import json
from typing import Final

import xbmc

import resources.lib.exporter as exporter
import resources.lib.importer as importer
import resources.lib.jsonrpc as jsonrpc
import resources.lib.media as media
import resources.lib.settings as settings
from resources.lib.addon import addon, player
from resources.lib.last_known import last_known
from resources.lib.sync import Sync
from resources.lib.timestamps import timestamps


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

        addon.set_logging(verbose=settings.ui.is_logging_verbose)
        addon.set_notifications(notify=settings.ui.should_show_notifications)

        self._active_sync = None
        self._waiting_sync = None
        self._waiting_actions = {}

        self._periodic_trigger = Alarm(
            name='periodic.trigger',
            command=f'NotifyAll({addon.id},{jsonrpc.INTERNAL_METHODS.patient_sync.send})',
            loop=True
        )
        self._waiter = Alarm(
            name='avoidance.wait',
            command=f'NotifyAll({addon.id},{jsonrpc.INTERNAL_METHODS.wait_done.send})'
        )

        if settings.triggers.should_sync_on_start:
            self._sync()
        elif settings.scheduled.is_enabled and settings.scheduled.should_run_missed_syncs:
            self._sync_if_scheduled()

        if settings.scheduled.is_enabled:
            self._update_schedule()

        self._periodic_trigger.set(settings.periodic.period)

        while not self.abortRequested():
            self.waitForAbort(60)
            self._sync_if_scheduled()

    def onNotification(self, sender: str, method: str, data: str) -> None:
        if self._active_sync and method == self._active_sync.awaiting:
            self._continue_sync()

        elif method == jsonrpc.INTERNAL_METHODS.immediate_sync.recv:
            self._sync()

        elif method == jsonrpc.INTERNAL_METHODS.patient_sync.recv:
            self._patient_sync()

        elif method == jsonrpc.INTERNAL_METHODS.sync_one.recv:
            self._waiting_actions['sync_one'] = data
            self._run_waiting_actions()

        elif method == jsonrpc.INTERNAL_METHODS.export.recv:
            self._waiting_actions['export'] = data
            self._run_waiting_actions()

        elif method == jsonrpc.INTERNAL_METHODS.export_all.recv:
            self._waiting_actions['export_all'] = data
            self._run_waiting_actions()

        elif method == jsonrpc.INTERNAL_METHODS.import_all.recv:
            self._waiting_actions['import_all'] = data
            self._run_waiting_actions()

        elif method == jsonrpc.INTERNAL_METHODS.wait_done.recv:
            self._wait_done()

        elif method == 'Player.OnPlay':
            self._waiter.cancel()

        elif method == 'Player.OnStop':
            self._play_stop()

        elif method == 'VideoLibrary.OnUpdate' and settings.triggers.should_export_on_update:
            self._library_update(data)

        elif method == 'VideoLibrary.OnScanFinished' and settings.triggers.should_sync_on_scan:
            self._patient_sync(was_triggered_by_scan=True)

    def onSettingsChanged(self) -> None:
        addon.set_logging(verbose=settings.ui.is_logging_verbose)
        addon.set_notifications(notify=settings.ui.should_show_notifications)

        if self._periodic_trigger.minutes != settings.periodic.period:
            self._periodic_trigger.set(settings.periodic.period)

        if self._waiter.is_active and self._waiter.minutes != settings.avoidance.wait_time:
            self._waiter.set(settings.avoidance.wait_time)

        if (self._waiting_sync and (not settings.avoidance.is_enabled
                                    or not settings.avoidance.wait_time and not player.isPlaying())):
            self._wait_done()

        if settings.scheduled.is_enabled:
            self._update_schedule()

    def _sync_if_scheduled(self) -> None:
        if not settings.scheduled.is_enabled:
            return
        if datetime.datetime.now() < timestamps.next_scheduled:
            return
        self._patient_sync()
        self._update_schedule()

    def _update_schedule(self) -> None:
        a_day = datetime.timedelta(days=1)

        next_sync = datetime.datetime.now()

        if next_sync.time() > settings.scheduled.time:
            next_sync += a_day

        while next_sync.weekday() not in settings.scheduled.days:
            next_sync += a_day

        next_sync = next_sync.replace(
            hour=settings.scheduled.time.hour,
            minute=settings.scheduled.time.minute,
            second=0,
            microsecond=0
        )

        timestamps.next_scheduled = next_sync

    def _sync(self) -> None:
        if self._active_sync:
            return
        self._active_sync = Sync()
        self._continue_sync()

    def _continue_sync(self) -> None:
        done = self._active_sync.resume()
        if done:
            self._active_sync = None
            self._run_waiting_actions()

    def _library_update(self, data: str) -> None:
        data = json.loads(data)
        item = data['item']

        # Always ignore added items if they aren't part a transaction because
        # refreshing an item will trigger a non-transactional update event.
        # We still want to update the checksum, however.
        if data.get('added') and (settings.triggers.ignores_add_updates or not data.get('transaction')):
            last_known.set_checksum(item['type'], item['id'])
            return

        if item['type'] in ['movie', 'tvshow', 'episode']:
            exporter.export(media.MediaInfo(type_=item['type'], id_=item['id']))

    def _patient_sync(self, was_triggered_by_scan: bool = False) -> None:
        if self._active_sync:
            return
        if (settings.avoidance.is_enabled and player.isPlaying()
                or self._waiter.is_active):
            self._waiting_sync = Sync(should_skip_scan=was_triggered_by_scan)
        else:
            self._sync()

    def _run_waiting_actions(self):
        if self._active_sync:
            return

        functions = {
            'sync_one': lambda a: Sync.sync_one(media.MediaInfo(type_=a['type'], id_=a['id'])),
            'export': lambda a: exporter.export(media.MediaInfo(type_=a['type'], id_=a['id'])),
            'export_all': lambda a: exporter.export_all(),
            'import_all': lambda a: importer.import_all()
        }

        for action in ['sync_one', 'export', 'export_all', 'import_all']:
            data = self._waiting_actions.pop(action, None)
            if data is None:
                continue
            functions[action](json.loads(data))

    def _play_stop(self):
        if settings.avoidance.wait_time:
            self._waiter.set(settings.avoidance.wait_time)
        elif self._waiting_sync:
            self._wait_done()

    def _wait_done(self) -> None:
        self._waiter.cancel()
        self._sync()
        self._waiting_sync = None


if __name__ == "__main__":
    Service()
