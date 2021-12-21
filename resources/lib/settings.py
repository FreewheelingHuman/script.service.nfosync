import datetime
import enum

from resources.lib.addon import addon


class MovieNfoOption(enum.Enum):
    MOVIE = 'movie'
    FILENAME = 'filename'


class ActorOption(enum.Enum):
    LEAVE = 'leave'
    UPDATE = 'update_by_name'
    OVERWRITE = 'overwrite'
    MERGE = 'merge_by_name'


class _Sync:

    @property
    def should_clean(self) -> bool:
        return addon.getSettingBool('sync.should_clean')

    @property
    def should_export(self) -> bool:
        return addon.getSettingBool('sync.should_export')

    @property
    def should_import(self) -> bool:
        return addon.getSettingBool('sync.should_import')

    @property
    def should_import_first(self) -> bool:
        return addon.getSettingBool('sync.should_import_first')

    @property
    def should_scan(self) -> bool:
        return addon.getSettingBool('sync.should_scan')


class _Export:

    @property
    def can_create_nfo(self) -> bool:
        return addon.getSettingBool('export.can_create_nfo')

    @property
    def movie_nfo_naming(self) -> MovieNfoOption:
        return MovieNfoOption(addon.getSettingString('export.movie_nfo_naming'))

    @property
    def should_ignore_new(self) -> bool:
        return addon.getSettingBool('export.should_ignore_new')

    @property
    def is_minimal(self) -> bool:
        return addon.getSettingBool('export.is_minimal')

    @property
    def can_overwrite(self) -> bool:
        return addon.getSettingBool('export.can_overwrite')

    @property
    def actor_handling(self) -> ActorOption:
        return ActorOption(addon.getSettingString('export.actor_handling'))

    @property
    def should_export_plugin_trailers(self) -> bool:
        return addon.getSettingBool('export.should_export_plugin_trailers')


class _Triggers:

    @property
    def should_sync_on_start(self) -> bool:
        return addon.getSettingBool('triggers.should_sync_on_start')

    @property
    def should_sync_on_scan(self) -> bool:
        return addon.getSettingBool('triggers.should_sync_on_scan')

    @property
    def should_export_on_update(self) -> bool:
        return addon.getSettingBool('triggers.should_export_on_update')


class _Avoidance:

    @property
    def is_enabled(self) -> bool:
        return addon.getSettingBool('avoidance.is_enabled')

    @property
    def wait_time(self) -> int:
        if self.is_enabled:
            return addon.getSettingInt('avoidance.wait_time')
        return 0


class _Periodic:

    @property
    def is_enabled(self) -> bool:
        return addon.getSettingBool('periodic.is_enabled')

    @property
    def period(self) -> int:
        if self.is_enabled:
            return addon.getSettingInt('periodic.period') * 60
        return 0


class _Scheduled:

    @property
    def is_enabled(self) -> bool:
        return addon.getSettingBool('scheduled.is_enabled') and addon.getSetting('scheduled.days') != ''

    @property
    def should_run_missed_syncs(self) -> bool:
        return addon.getSettingBool('scheduled.should_run_missed_syncs')

    @property
    def time(self) -> datetime.time:
        time = addon.getSettingString('scheduled.time').split(':')
        return datetime.time(hour=int(time[0]), minute=int(time[1]))

    @property
    def days(self) -> list:
        return [int(day) for day in addon.getSetting('scheduled.days').split(',')]


class _UI:

    @property
    def should_show_sync(self) -> bool:
        return addon.getSettingBool('ui.should_show_sync')

    @property
    def should_show_notifications(self) -> bool:
        return addon.getSettingBool('ui.should_show_notifications')

    @property
    def is_logging_verbose(self) -> bool:
        return addon.getSettingBool('ui.is_logging_verbose')


sync = _Sync()
export = _Export()
triggers = _Triggers()
avoidance = _Avoidance()
periodic = _Periodic()
scheduled = _Scheduled()
ui = _UI()
