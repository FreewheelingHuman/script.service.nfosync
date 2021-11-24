import enum
import json
from typing import Final, Optional

import resources.lib.utcdt as utcdt
from resources.lib.addon import ADDON


class MovieNfoType(enum.Enum):
    MOVIE = 'movie'
    FILENAME = 'filename'


class ActorTagOption(enum.Enum):
    SKIP = 'skip'
    UPDATE = 'update_by_name'
    OVERWRITE = 'overwrite'
    MERGE = 'merge_by_name'


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

    class _RefreshExceptions:
        _refresh_exceptions: Final = 'state.refresh_exceptions'

        def __init__(self):
            self._cache = json.loads(ADDON.getSettingString(self._refresh_exceptions))

        def __getitem__(self, file: str) -> utcdt.Dt:
            return utcdt.fromisoformat(self._cache[file])

        def __setitem__(self, file: str, timestamp: utcdt.Dt) -> None:
            self._cache[file] = timestamp.isoformat(timespec='seconds')
            ADDON.setSettingString(self._refresh_exceptions, json.dumps(self._cache))

        def clear(self) -> None:
            self._cache = {}
            ADDON.setSettingString(self._refresh_exceptions, '{}')

    def __init__(self):
        self._refresh_exceptions_wrapper: Final = self._RefreshExceptions()

    @property
    def last_refresh(self) -> Optional[utcdt.Dt]:
        iso_string = ADDON.getSetting(self._last_refresh)
        if iso_string == '':
            return None

        last_scan = utcdt.fromisoformat(iso_string)

        return last_scan

    @last_refresh.setter
    def last_refresh(self, value: utcdt.Dt) -> None:
        ADDON.setSetting(self._last_refresh, value.isoformat(timespec='seconds'))

    @property
    def refresh_exceptions(self) -> _RefreshExceptions:
        return self._refresh_exceptions_wrapper


SYNC = _Sync()
TRIGGERS = _Triggers()
AVOIDANCE = _Avoidance()
PERIODIC = _Periodic()
STATE = _State()
