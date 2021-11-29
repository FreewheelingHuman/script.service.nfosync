import enum
import json
from typing import Final, Optional

import resources.lib.utcdt as utcdt
from resources.lib.addon import ADDON
from resources.lib.tracker import Tracker


class MovieNfoType(enum.Enum):
    MOVIE = 'movie'
    FILENAME = 'filename'


class ActorTagOption(enum.Enum):
    SKIP = 'skip'
    UPDATE = 'update_by_name'
    OVERWRITE = 'overwrite'
    MERGE = 'merge_by_name'


class TrailerTagOption(enum.Enum):
    SKIP = 'skip'
    NO_LOCAL = 'no_local'
    NO_PLUGIN = 'no_plugin'


class _Sync:

    @property
    def clean(self) -> bool:
        return ADDON.getSettingBool('sync.clean')

    @property
    def export(self) -> bool:
        return ADDON.getSettingBool('sync.export')

    @property
    def create_nfo(self) -> bool:
        return ADDON.getSettingBool('sync.create_nfo')

    @property
    def movie_nfo(self) -> MovieNfoType:
        return MovieNfoType(ADDON.getSettingString('sync.create_nfo'))

    @property
    def imprt(self) -> bool:
        return ADDON.getSettingBool('sync.import')

    @property
    def imprt_first(self) -> bool:
        return ADDON.getSettingBool('sync.import_first')

    @property
    def scan(self) -> bool:
        return ADDON.getSettingBool('sync.scan')

    @property
    def visible(self) -> bool:
        return ADDON.getSettingBool('sync.visible')

    @property
    def actor(self) -> ActorTagOption:
        return ActorTagOption(ADDON.getSettingString('sync.actor'))

    @property
    def trailer(self) -> TrailerTagOption:
        return TrailerTagOption('no_local')  # Dummy until the actual setting gets added


class _Triggers:

    @property
    def start(self) -> bool:
        return ADDON.getSettingBool('triggers.start')

    @property
    def scan(self) -> bool:
        return ADDON.getSettingBool('triggers.scan')

    @property
    def update(self) -> bool:
        return ADDON.getSettingBool('triggers.update')

    @property
    def ignore_added(self) -> bool:
        return ADDON.getSettingBool('triggers.ignore_added')


class _Avoidance:

    @property
    def enabled(self) -> bool:
        return ADDON.getSettingBool('avoidance.enabled')

    @property
    def wait(self) -> int:
        if self.enabled:
            return ADDON.getSettingInt('avoidance.wait')
        return 0


class _Periodic:

    @property
    def enabled(self) -> bool:
        return ADDON.getSettingBool('periodic.enabled')

    @property
    def period(self) -> int:
        return ADDON.getSettingInt('periodic.period') * 60


class _State:
    _last_refresh: Final = 'state.last_refresh'

    def __init__(self):
        self._trackers = {
            'movie': Tracker('movies'),
            'movieset': Tracker('moviesets'),
            'episode': Tracker('episodes'),
            'tvshow': Tracker('tvshows')
        }

    @property
    def last_refresh(self) -> Optional[utcdt.UtcDt]:
        iso_string = ADDON.getSetting(self._last_refresh)
        if iso_string == '':
            return None

        last_scan = utcdt.fromisoformat(iso_string)

        return last_scan

    @last_refresh.setter
    def last_refresh(self, value: utcdt.UtcDt) -> None:
        ADDON.setSetting(self._last_refresh, value.isoformat(timespec='seconds'))

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
        for media_type, tracker in self._trackers:
            tracker.write()


SYNC = _Sync()
TRIGGERS = _Triggers()
AVOIDANCE = _Avoidance()
PERIODIC = _Periodic()
STATE = _State()
