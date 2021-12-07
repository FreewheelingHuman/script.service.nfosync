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


class TrailerOption(enum.Enum):
    DEFAULT = 'default'
    SKIP = 'skip'
    NO_PLUGIN = 'no_plugin'


class _Sync:

    @property
    def should_clean(self) -> bool:
        return addon.getSettingBool('sync.should_clean')

    @property
    def should_export(self) -> bool:
        return addon.getSettingBool('sync.should_export')

    @property
    def can_create_nfo(self) -> bool:
        return addon.getSettingBool('sync.can_create_nfo')

    @property
    def movie_nfo_naming(self) -> MovieNfoOption:
        return MovieNfoOption(addon.getSettingString('sync.movie_nfo_naming'))

    @property
    def should_import(self) -> bool:
        return addon.getSettingBool('sync.should_import')

    @property
    def should_import_first(self) -> bool:
        return addon.getSettingBool('sync.should_import_first')

    @property
    def should_scan(self) -> bool:
        return addon.getSettingBool('sync.should_scan')

    @property
    def actor_handling(self) -> ActorOption:
        return ActorOption(addon.getSettingString('sync.actor_handling'))

    @property
    def trailer_handling(self) -> TrailerOption:
        return TrailerOption('default')  # Dummy until the actual setting gets added


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

    @property
    def ignores_add_updates(self) -> bool:
        return addon.getSettingBool('triggers.ignores_add_updates')


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


class _UI:

    @property
    def should_show_sync(self) -> bool:
        return True  # Placeholder until settings adjusted

    @property
    def should_show_notifications(self) -> bool:
        return True  # Placeholder until real setting added

    @property
    def is_logging_verbose(self) -> bool:
        return True  # Placeholder until real setting added


sync = _Sync()
triggers = _Triggers()
avoidance = _Avoidance()
periodic = _Periodic()
ui = _UI()
