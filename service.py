import collections
import datetime
import json
from typing import Final

import xbmc

import resources.lib.actions as actions
import resources.lib.jsonrpc as jsonrpc
import resources.lib.media as media
import resources.lib.settings as settings
from resources.lib.addon import addon, player
from resources.lib.last_known import last_known
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

    _limited_actions: Final = ['Sync All', 'Import All', 'Export All']

    def __init__(self):
        super().__init__()

        addon.set_logging(verbose=settings.ui.is_logging_verbose)
        addon.set_notifications(notify=settings.ui.should_show_notifications)

        self._active_action = None
        self._action_queue = collections.deque()
        self._patient_action_queue = collections.deque()

        self._periodic_trigger = Alarm(
            name='periodic.trigger',
            command=f'NotifyAll({addon.id},{jsonrpc.INTERNAL_METHODS.sync_all.send},{{"patient":true}})',
            loop=True
        )
        self._waiter = Alarm(
            name='avoidance.wait',
            command=f'NotifyAll({addon.id},{jsonrpc.INTERNAL_METHODS.wait_done.send})'
        )

        if settings.triggers.should_sync_on_start:
            self._queue_action(actions.SyncAll(), patient=False)
        elif self._is_scheduled_sync_due() and settings.scheduled.should_run_missed_syncs:
            self._queue_action(actions.SyncAll(), patient=False)

        if settings.scheduled.is_enabled:
            self._update_schedule()

        self._periodic_trigger.set(settings.periodic.period)

        while not self.abortRequested():
            self.waitForAbort(60)
            if self._is_scheduled_sync_due():
                self._queue_action(actions.SyncAll(), patient=True)
                self._update_schedule()

    def onNotification(self, sender: str, method: str, data: str) -> None:
        data = json.loads(data)

        if self._active_action and method == self._active_action.awaiting:
            self._continue_actions()

        elif method == jsonrpc.INTERNAL_METHODS.sync_all.recv:
            self._queue_action(actions.SyncAll(), patient=data['patient'])

        elif method == jsonrpc.INTERNAL_METHODS.sync_one.recv:
            info = media.MediaInfo(data['type'], data['id'])
            self._queue_action(actions.SyncOne(info), patient=data['patient'])

        elif method == jsonrpc.INTERNAL_METHODS.import_all.recv:
            self._queue_action(actions.ImportAll(), patient=data['patient'])

        elif method == jsonrpc.INTERNAL_METHODS.export_one.recv:
            info = media.MediaInfo(data['type'], data['id'])
            self._queue_action(actions.ExportOne(info), patient=data['patient'])

        elif method == jsonrpc.INTERNAL_METHODS.export_all.recv:
            self._queue_action(actions.ExportAll(), patient=data['patient'])

        elif method == jsonrpc.INTERNAL_METHODS.wait_done.recv:
            self._wait_done()

        elif method == 'Player.OnPlay':
            self._waiter.cancel()

        elif method == 'Player.OnStop':
            self._play_stop()

        elif method == 'VideoLibrary.OnUpdate' and settings.triggers.should_export_on_update:
            self._library_update(data)

        elif method == 'VideoLibrary.OnScanFinished' and settings.triggers.should_sync_on_scan:
            self._queue_action(actions.SyncAll(should_skip_scan=True), patient=True)

    def onSettingsChanged(self) -> None:
        addon.set_logging(verbose=settings.ui.is_logging_verbose)
        addon.set_notifications(notify=settings.ui.should_show_notifications)

        if self._periodic_trigger.minutes != settings.periodic.period:
            self._periodic_trigger.set(settings.periodic.period)

        if self._waiter.is_active and self._waiter.minutes != settings.avoidance.wait_time:
            self._waiter.set(settings.avoidance.wait_time)

        if settings.scheduled.is_enabled:
            self._update_schedule()

        self._run_actions()

    def _is_scheduled_sync_due(self) -> bool:
        if not settings.scheduled.is_enabled:
            return False
        if datetime.datetime.now() < timestamps.next_scheduled:
            return False

        return True

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

    def _library_update(self, data: dict) -> None:
        item = data['item']

        # Always ignore added items if they aren't part a transaction because
        # refreshing an item will trigger a non-transactional update event.
        # We still want to update the checksum, however.
        if data.get('added') and (settings.triggers.ignores_add_updates or not data.get('transaction')):
            last_known.set_checksum(item['type'], item['id'])
            return

        if item['type'] in ['movie', 'tvshow', 'episode']:
            info = media.MediaInfo(item['type'], item['id'])
            self._queue_action(actions.ExportOne(info), patient=False)

    def _play_stop(self):
        if settings.avoidance.wait_time:
            self._waiter.set(settings.avoidance.wait_time)
        else:
            self._wait_done()

    def _wait_done(self) -> None:
        self._waiter.cancel()
        self._run_actions()

    @property
    def _queued_types(self) -> set:
        types = set()
        if self._active_action:
            types.add(self._active_action.type)
        for action in self._action_queue:
            types.add(action.type)
        for action in self._patient_action_queue:
            types.add(action.type)
        return types

    @property
    def _can_patient_actions_run(self) -> bool:
        if (settings.avoidance.is_enabled and player.isPlaying()) or self._waiter.is_active:
            return False
        return True

    def _run_actions(self):
        if self._active_action:
            return

        while self._action_queue:
            self._active_action = self._action_queue.pop()
            self._active_action.run()
            if not self._active_action.is_done:
                return

        while self._patient_action_queue and self._can_patient_actions_run:
            self._active_action = self._patient_action_queue.pop()
            self._active_action.run()
            if not self._active_action.is_done:
                return

    def _continue_actions(self):
        self._active_action.run()
        if self._active_action.is_done:
            self._active_action = None
            self._run_actions()

    def _queue_action(self, action: actions.Action, patient: bool):
        if action.type in self._limited_actions and action.type in self._queued_types:
            return

        if patient:
            self._patient_action_queue.append(action)
        else:
            self._action_queue.append(action)

        self._run_actions()


if __name__ == "__main__":
    Service()
