from typing import Final, Optional

import xbmcvfs

from resources.lib.addon import ADDON
from resources.lib.log import log


class _NoMoreBytes(Exception):
    pass


class _ByteReader:
    def __init__(self, byts: bytearray):
        self._byts = byts
        self._cursor = 0

    def advance(self, byts_to_advance: int):
        self._cursor += byts_to_advance

    def read(self, byts_to_read: int) -> bytearray:
        end_point = self._cursor + byts_to_read
        result = self._byts[self._cursor:end_point]
        self._cursor = end_point

        if not result:
            raise _NoMoreBytes

        return result


class Tracker:
    _version_bytes: Final = 2
    _library_id_bytes: Final = 4
    _status_bits_bytes: Final = 1
    _checksum_bytes: Final = 4
    _timestamp_bytes: Final = 5

    _checksum_index: Final = 0
    _timestamp_index: Final = 1

    _version: Final = 0

    def __init__(self, name: str):
        self._contents = {}
        self._changes = False
        self._file_path: Final = xbmcvfs.translatePath(f'{ADDON.profile}{name}.dat')

        if not xbmcvfs.exists(self._file_path):
            return

        with xbmcvfs.File(self._file_path) as file:
            byts = file.readBytes()
            self._import_byts(byts)

    def get(self, library_id: int, field: str) -> Optional[int]:
        record = self._contents.get(library_id, None)
        if record is None:
            return None
        value = record.get(field, None)
        return value

    def set(self, library_id: int, field: str, value: int) -> None:
        self._changes = True
        if library_id not in self._contents:
            self._contents[library_id] = {}
        self._contents[library_id][field] = value

    def delete(self, library_id: int) -> None:
        del self._contents[library_id]

    def write(self) -> None:
        if not self._changes:
            return

        byts_to_write = bytearray()

        byts_to_write.extend(self._version.to_bytes(self._version_bytes, byteorder='little'))

        for library_id, fields in self._contents.items():
            byts_to_write.extend(library_id.to_bytes(self._library_id_bytes, byteorder='little'))

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

            byts_to_write.extend(status_bits.to_bytes(self._status_bits_bytes, byteorder='little'))
            byts_to_write.extend(checksum.to_bytes(self._checksum_bytes, byteorder='little'))
            byts_to_write.extend(timestamp.to_bytes(self._timestamp_bytes, byteorder='little'))

        with xbmcvfs.File(self._file_path, 'w') as file:
            success = file.write(byts_to_write)

        if not success:
            log(f'Unable to write tracker file "{self._file_path}"')

    def _import_byts(self, byts: bytearray) -> None:
        byte_reader = _ByteReader(byts)
        byte_reader.advance(self._version_bytes)  # skip over version info, it's not used right now

        while True:
            record = {}

            try:
                library_id = int.from_bytes(byte_reader.read(self._library_id_bytes), byteorder='little')
                status_bits = int.from_bytes(byte_reader.read(self._status_bits_bytes), byteorder='little')
                checksum = int.from_bytes(byte_reader.read(self._checksum_bytes), byteorder='little')
                timestamp = int.from_bytes(byte_reader.read(self._timestamp_bytes), byteorder='little')
            except _NoMoreBytes:
                break

            if self._get_bit(status_bits, self._checksum_index):
                record['checksum'] = checksum
            if self._get_bit(status_bits, self._timestamp_index):
                record['timestamp'] = timestamp
            if record:
                self._contents[library_id] = record

    def _get_bit(self, bit_array: int, index: int) -> int:
        return bit_array & (1 << index)

    def _set_bit(self, bit_array: int, index: int) -> int:
        return bit_array | (1 << index)
