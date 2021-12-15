from collections import deque
from typing import Final

import xbmcgui

import resources.lib.exporter as exporter
import resources.lib.importer as importer
import resources.lib.jsonrpc as jsonrpc
import resources.lib.media as media
import resources.lib.settings as settings
import resources.lib.utcdt as utcdt
from resources.lib.addon import addon
from resources.lib.last_known import last_known
from resources.lib.timestamps import timestamps


class Sync:
    _progress_bar: Final = xbmcgui.DialogProgressBG()

    def __init__(self, should_skip_scan: bool = False):
        # Create a local copy of all settings in case they change mid-sync
        self._should_clean = settings.sync.should_clean
        self._should_import = settings.sync.should_import
        self._should_import_first = settings.sync.should_import_first
        self._should_export = settings.sync.should_export
        self._should_scan = settings.sync.should_scan

        self._stages = deque()
        if self._should_clean:
            self._stages.append(self._clean)
        if self._should_import or self._should_export:
            self._stages.append(self._sync_changes)
        if self._scan and not should_skip_scan:
            self._stages.append(self._scan)
        self._stage_count = len(self._stages)

        self._last_sync = timestamps.last_sync

        self._should_show = settings.ui.should_show_sync
        self._progress_bar_up = False

        self._awaiting = None

        self._failures = False

    @property
    def awaiting(self) -> str:
        return self._awaiting

    # Returns true when it is done
    def resume(self) -> bool:
        while self._stages:
            self._stages[0]()
            self._stages.popleft()
            if self._awaiting:
                return False

        last_known.write_changes()
        self._close_dialog()

        if self._failures:
            addon.notify(32064)

        return True

    @classmethod
    def start(cls, should_skip_scan: bool = False) -> ('Sync', bool):
        sync = cls(should_skip_scan=should_skip_scan)
        return sync, sync.resume()

    @classmethod
    def sync_one(cls, info: media.MediaInfo) -> None:
        sync = cls()
        sync._sync_item(info)
        if sync._failures:
            addon.notify(32064)

    def _clean(self) -> None:
        self._update_dialog(32003)
        jsonrpc.request('VideoLibrary.Clean', showdialogs=False)
        self._awaiting = 'VideoLibrary.OnCleanFinished'

    def _sync_changes(self) -> None:
        self._update_dialog(32010)

        scan_time = utcdt.now()

        for movie in media.get_all('movie'):
            self._sync_item(media.MediaInfo('movie', movie['movieid'], file=movie['file']))

        for tvshow in media.get_all('tvshow'):
            self._sync_item(media.MediaInfo('tvshow', tvshow['tvshowid'], file=tvshow['file']))

        for episode in media.get_all('episode'):
            self._sync_item(media.MediaInfo('episode', episode['episodeid'], file=episode['file']))

        timestamps.last_sync = scan_time

        self._awaiting = None

    def _sync_item(self, info: media.MediaInfo) -> None:
        should_import = self._item_requires_import(info) if self._should_import else False

        if self._should_export:
            self._export_if_needed(info, should_import)

        if should_import:
            importer.import_(info)

    def _item_requires_import(self, info: media.MediaInfo) -> bool:
        modification_time = info.nfo_modification_time()
        if modification_time is None:
            return False

        last_modification_time = last_known.timestamp(info.type, info.id)
        if last_modification_time is None:
            last_modification_time = self._last_sync

        if modification_time > last_modification_time:
            return True

        return False

    def _export_if_needed(self, info: media.MediaInfo, should_import: bool) -> None:
        last_checksum = last_known.checksum(info.type, info.id)

        if last_checksum == info.checksum:
            return
        addon.log(f'Sync - Exporting "{info.details["title"]}" due to checksum difference.')

        overwrite = not should_import if self._should_import_first else None
        success = exporter.export(subtask=True, info=info, overwrite=overwrite)

        if not success:
            self._failures = True

    def _scan(self) -> None:
        self._update_dialog(32012)
        jsonrpc.request('VideoLibrary.Scan', showdialogs=False)
        self._awaiting = 'VideoLibrary.OnScanFinished'

    def _close_dialog(self) -> None:
        if self._progress_bar_up:
            self._progress_bar.close()
            self._progress_bar_up = False

    def _update_dialog(self, message_num: int) -> None:
        if not self._should_show:
            return

        heading = addon.getLocalizedString(32011)
        message = addon.getLocalizedString(message_num)

        if self._progress_bar_up:
            progress = int((1 - (len(self._stages) / self._stage_count)) * 100)
            self._progress_bar.update(progress, heading, message)
        else:
            self._progress_bar.create(heading, message)
            self._progress_bar_up = True
