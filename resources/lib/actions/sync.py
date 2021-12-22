from typing import Iterator, Final

import resources.lib.gui as gui
import resources.lib.jsonrpc as jsonrpc
import resources.lib.media as media
import resources.lib.settings as settings
import resources.lib.utcdt as utcdt
from resources.lib.last_known import last_known
from resources.lib.timestamps import timestamps

from . import *
from . import _PhasedAction, _RequestResponseAction


class SyncOne(_PhasedAction):

    _type: Final = 'Sync One'

    def __init__(self, info: media.MediaInfo):
        super().__init__()
        self._info = info

    def _phases(self) -> Iterator[Action]:
        should_import = self._item_requires_import()
        should_export = self._item_requires_export()

        if should_export:
            overwrite = not should_import if settings.sync.should_import_first else None
            yield ExportOne(self._info, overwrite=overwrite)

        if should_import:
            yield ImportOne(self._info)

    def _exception(self, error: Exception) -> None:
        if isinstance(error, ActionError):
            raise ActionError(32086, f'Sync - Unable to Sync "{self._info.file}"') from error
        super()._exception(error)

    def _item_requires_import(self) -> bool:
        modification_time = self._info.nfo_modification_time()
        if modification_time is None:
            return False

        last_modification_time = last_known.timestamp(self._info.type, self._info.id)
        if last_modification_time is None:
            last_modification_time = timestamps.last_sync

        if modification_time > last_modification_time:
            return True

        return False

    def _item_requires_export(self) -> bool:
        last_checksum = last_known.checksum(self._info.type, self._info.id)

        if last_checksum == self._info.checksum:
            return False

        return True


_sync_progress: Final = gui.SyncProgress()


class _Clean(_RequestResponseAction):

    _type: Final = 'Clean'

    def _request(self) -> None:
        _sync_progress.set(32003, 0, 1)
        jsonrpc.request('VideoLibrary.Clean', showdialogs=False)
        self._awaiting = 'VideoLibrary.OnCleanFinished'


class _SyncChangesByType(_PhasedAction):

    _type: Final = 'Sync Changes By Type'

    def __init__(self, type_: str, message: int):
        super().__init__()
        self._media_type = type_
        self._message = message

    def _phases(self) -> Iterator[Action]:
        type_info = media.TYPE_INFO[self._media_type]
        items = media.get_all(self._media_type)
        count = 0
        total = len(items)
        for item in items:
            _sync_progress.set(self._message, count, total)
            yield SyncOne(media.MediaInfo(self._media_type, item[type_info.id_name], file=item['file']))
            count += 1


class _SyncChanges(_PhasedAction):

    _type: Final = 'Sync Changes'

    _types_to_sync = {
        'movie': 32010,
        'tvshow': 32012,
        'episode': 32084
    }

    def _phases(self) -> Iterator[Action]:
        scan_time = utcdt.now()

        for type_, message in self._types_to_sync.items():
            yield _SyncChangesByType(type_=type_, message=message)

        timestamps.last_sync = scan_time


class _Scan(_RequestResponseAction):

    _type: Final = 'Scan'

    def _request(self) -> None:
        jsonrpc.request('VideoLibrary.Scan', showdialogs=settings.ui.should_show_sync)
        self._awaiting = 'VideoLibrary.OnScanFinished'


class SyncAll(_PhasedAction):

    _type: Final = 'Sync All'

    def __init__(self, should_skip_scan: bool = False):
        super().__init__()
        self._should_skip_scan = should_skip_scan

    def _phases(self) -> Iterator[Action]:
        if settings.sync.should_clean:
            yield _Clean()

        if settings.sync.should_import or settings.sync.should_export:
            yield _SyncChanges()

        _sync_progress.close()

        if settings.sync.should_scan and not self._should_skip_scan:
            yield _Scan()

    def _cleanup(self) -> None:
        _sync_progress.close()

    def _exception(self, error: Exception) -> None:
        if isinstance(error, ActionError):
            raise ActionError(32064, f'Sync - Unable to complete Sync All"') from error
        super()._exception(error)
