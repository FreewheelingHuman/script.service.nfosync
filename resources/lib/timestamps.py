import datetime
import json
import resources.lib.utcdt as utcdt

import xbmcvfs

from resources.lib.addon import addon


class _Timestamps:
    def __init__(self):
        self._file = xbmcvfs.translatePath(f'{addon.profile}timestamps.json')

        with xbmcvfs.File(self._file) as file:
            raw_json = file.read()

        if raw_json == '':
            contents = {}
        else:
            contents = json.loads(raw_json)

        last_sync = contents.get('sync_timestamp')
        if last_sync is None:
            self._last_sync = utcdt.now()
        else:
            self._last_sync = utcdt.fromisoformat(last_sync)

        next_scheduled = contents.get('next_scheduled')
        if next_scheduled is None:
            self._next_scheduled = datetime.datetime(year=1980, month=1, day=1)
        else:
            self._next_scheduled = datetime.datetime.fromisoformat(next_scheduled)

        self._write()

    @property
    def last_sync(self) -> utcdt.UtcDt:
        return self._last_sync

    @last_sync.setter
    def last_sync(self, timestamp: utcdt.UtcDt) -> None:
        self._last_sync = timestamp
        self._write()

    @property
    def next_scheduled(self) -> datetime.datetime:
        return self._next_scheduled

    @next_scheduled.setter
    def next_scheduled(self, timestamp: datetime.datetime) -> None:
        self._next_scheduled = timestamp
        self._write()

    def _write(self):
        contents = {
            'last_sync': self._last_sync.isoformat(timespec='seconds'),
            'next_scheduled': self._next_scheduled.isoformat(timespec='seconds')
        }

        with xbmcvfs.File(self._file, 'w') as file:
            success = file.write(json.dumps(contents))

        if not success:
            addon.log(f'Unable to write timestamps file "{self._file}"')
            addon.notify(32006)


timestamps = _Timestamps()
