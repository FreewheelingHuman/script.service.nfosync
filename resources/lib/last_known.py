from typing import Final, Optional

import xbmcvfs

import resources.lib.media as media
import resources.lib.utcdt as utcdt
from resources.lib.addon import addon


class _NoMoreBytes(Exception):
    pass


class _ByteReader:
    def __init__(self, bytes_: bytearray):
        self._bytes = bytes_
        self._cursor = 0

    def advance(self, bytes_: int) -> None:
        self._cursor += bytes_

    def read(self, bytes_: int) -> bytearray:
        end_point = self._cursor + bytes_
        result = self._bytes[self._cursor:end_point]
        self._cursor = end_point

        if not result:
            raise _NoMoreBytes

        return result


class _Tracker:
    _version_bytes: Final = 2
    _id_bytes: Final = 4
    _status_bytes: Final = 1
    _checksum_bytes: Final = 4
    _timestamp_bytes: Final = 5

    _checksum_index: Final = 0
    _timestamp_index: Final = 1

    _version: Final = 0

    def __init__(self, name: str):
        self._contents = {}
        self._has_unwritten_changes = False
        self._file: Final = xbmcvfs.translatePath(f'{addon.profile}{name}.dat')

        if not xbmcvfs.exists(self._file):
            return

        with xbmcvfs.File(self._file) as file:
            bytes_ = file.readBytes()
            self._import_bytes(bytes_)

    def get(self, id_: int, field: str) -> Optional[int]:
        record = self._contents.get(id_, None)
        if record is None:
            return None
        return record.get(field, None)

    def set(self, id_: int, field: str, value: int) -> None:
        self._has_unwritten_changes = True
        if id_ not in self._contents:
            self._contents[id_] = {}
        self._contents[id_][field] = value

    def delete(self, id_: int) -> None:
        del self._contents[id_]

    def write(self) -> None:
        if not self._has_unwritten_changes:
            return

        bytes_ = bytearray()

        bytes_.extend(self._version.to_bytes(self._version_bytes, byteorder='little'))

        for id_, fields in self._contents.items():
            bytes_.extend(id_.to_bytes(self._id_bytes, byteorder='little'))

            status_bits = 0

            checksum = fields.get('checksum', None)
            if checksum is None:
                checksum = 0
            else:
                status_bits = self._set_bit(status_bits, self._checksum_index)

            timestamp = fields.get('timestamp', None)
            if timestamp is None:
                timestamp = 0
            else:
                status_bits = self._set_bit(status_bits, self._timestamp_index)

            bytes_.extend(status_bits.to_bytes(self._status_bytes, byteorder='little'))
            bytes_.extend(checksum.to_bytes(self._checksum_bytes, byteorder='little'))
            bytes_.extend(timestamp.to_bytes(self._timestamp_bytes, byteorder='little'))

        xbmcvfs.mkdir(addon.profile)
        with xbmcvfs.File(self._file, 'w') as file:
            success = file.write(bytes_)

        if not success:
            addon.log(f'Unable to write tracker file "{self._file}"')

    def _import_bytes(self, bytes_: bytearray) -> None:
        byte_reader = _ByteReader(bytes_)
        byte_reader.advance(self._version_bytes)  # skip over version info, it's not used right now

        while True:
            record = {}

            try:
                id_ = int.from_bytes(byte_reader.read(self._id_bytes), byteorder='little')
                status = int.from_bytes(byte_reader.read(self._status_bytes), byteorder='little')
                checksum = int.from_bytes(byte_reader.read(self._checksum_bytes), byteorder='little')
                timestamp = int.from_bytes(byte_reader.read(self._timestamp_bytes), byteorder='little')
            except _NoMoreBytes:
                break

            if self._get_bit(status, self._checksum_index):
                record['checksum'] = checksum
            if self._get_bit(status, self._timestamp_index):
                record['timestamp'] = timestamp
            if record:
                self._contents[id_] = record

    def _get_bit(self, bit_array: int, index: int) -> int:
        return bit_array & (1 << index)

    def _set_bit(self, bit_array: int, index: int) -> int:
        return bit_array | (1 << index)


class _LastKnown:
    def __init__(self):
        self._trackers = {
            'movie': _Tracker('movies'),
            'episode': _Tracker('episodes'),
            'tvshow': _Tracker('tvshows')
        }

    def checksum(self, type_: str, id_: int) -> Optional[int]:
        return self._trackers[type_].get(id_, 'checksum')

    def set_checksum(self, type_: str, id_: int, checksum: Optional[int]) -> None:
        if checksum is None:
            checksum = media.MediaInfo(type_, id_).checksum
        self._trackers[type_].set(id_, 'checksum', checksum)

    def timestamp(self, type_: str, id_: int) -> Optional[utcdt.UtcDt]:
        epoch_timestamp = self._trackers[type_].get(id_, 'timestamp')
        if epoch_timestamp is None:
            return None
        return utcdt.fromtimestamp(epoch_timestamp)

    def set_timestamp(self, type_: str, id_: int, timestamp: utcdt.UtcDt) -> None:
        epoch_timestamp = int(timestamp.timestamp())
        self._trackers[type_].set(id_, 'timestamp', epoch_timestamp)

    def write_changes(self):
        for tracker in self._trackers.values():
            tracker.write()


last_known = _LastKnown()
