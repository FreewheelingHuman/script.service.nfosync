import collections
import datetime
import json
from typing import Final

import xbmc

import resources.lib.actions as actions
import resources.lib.jsonrpc as jsonrpc
import resources.lib.media as media
import resources.lib.settings as settings
import resources.lib.utcdt as utcdt
from resources.lib.addon import addon, player
from resources.lib.alarm import Alarm
from resources.lib.last_known import last_known
from resources.lib.timestamps import timestamps


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
            name='Service.PeriodicTrigger',
            message=jsonrpc.INTERNAL_METHODS.sync_all.send,
            data={'patient': True},
            loop=True
        )
        self._waiter = Alarm(
            name='Service.AvoidanceWait',
            message=jsonrpc.INTERNAL_METHODS.wait_done.send
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

        last_known.write_changes()

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
            self._run_actions()

        elif method == jsonrpc.INTERNAL_METHODS.write_changes.recv:
            self._queue_action(actions.WriteChanges(), patient=data['patient'])

        elif method == 'Player.OnPlay':
            self._waiter.cancel()

        elif method == 'Player.OnStop':
            self._play_stop()

        elif method == 'VideoLibrary.OnUpdate':
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

        if item['type'] not in ['movie', 'tvshow', 'episode']:
            return

        if not settings.triggers.should_export_on_update:
            if data.get('added'):
                last_known.set_timestamp(item['type'], item['id'], utcdt.now())
                if settings.export.should_ignore_new:
                    last_known.set_checksum(item['type'], item['id'])
            return

        if data.get('added') and (settings.export.should_ignore_new or not data.get('transaction')):
            last_known.set_timestamp(item['type'], item['id'], utcdt.now())
            last_known.set_checksum(item['type'], item['id'])
            return

        info = media.MediaInfo(item['type'], item['id'])
        self._queue_action(actions.ExportOne(info), patient=False)

    def _play_stop(self):
        if settings.avoidance.wait_time:
            self._waiter.set(settings.avoidance.wait_time)
        else:
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

        self._active_action = None

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
