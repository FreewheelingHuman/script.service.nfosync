import enum
from typing import Final, Optional

import resources.lib.utcdt as utcdt
from resources.lib.addon import addon
from resources.lib.tracker import Tracker


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


class _State:
    _last_refresh: Final = 'state.last_refresh'

    def __init__(self):
        self._trackers = {
            'movie': Tracker('movies'),
            'episode': Tracker('episodes'),
            'tvshow': Tracker('tvshows')
        }

    @property
    def last_refresh(self) -> Optional[utcdt.UtcDt]:
        iso_string = addon.getSetting(self._last_refresh)
        if iso_string == '':
            return None

        last_scan = utcdt.fromisoformat(iso_string)

        return last_scan

    @last_refresh.setter
    def last_refresh(self, value: utcdt.UtcDt) -> None:
        addon.setSetting(self._last_refresh, value.isoformat(timespec='seconds'))

    def get_checksum(self, media_type: str, library_id: int) -> Optional[int]:
        return self._trackers[media_type].get(library_id, 'checksum')

    def set_checksum(self, media_type: str, library_id: int, checksum: int) -> None:
        self._trackers[media_type].set(library_id, checksum)

    def get_timestamp(self, media_type: str, library_id: int) -> Optional[utcdt.UtcDt]:
        epoch_timestamp = self._trackers[media_type].get(library_id, 'timestamp')
        if epoch_timestamp is None:
            return None
        dt = utcdt.fromtimestamp(epoch_timestamp)
        return dt

    def set_timestamp(self, media_type: str, library_id: int, timestamp: utcdt.UtcDt) -> None:
        epoch_timestamp = int(timestamp.timestamp())
        self._trackers[media_type].set(library_id, 'timestamp', epoch_timestamp)

    def write_changes(self):
        for media_type, tracker in self._trackers.items():
            tracker.write()


sync = _Sync()
triggers = _Triggers()
avoidance = _Avoidance()
periodic = _Periodic()
ui = _UI()
state = _State()
