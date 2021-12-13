from collections import deque
from typing import Final

import xbmcgui

import resources.lib.exporter as exporter
import resources.lib.jsonrpc as jsonrpc
import resources.lib.media as media
import resources.lib.settings as settings
import resources.lib.utcdt as utcdt
from resources.lib.addon import addon
from resources.lib.last_known import last_known


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

        self._last_scan = last_known.sync_timestamp

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
        sync = cls(should_skip_scan)
        return sync, sync.resume()

    def _clean(self) -> None:
        addon.log("Starting clean", verbose=True)
        self._update_dialog(32003)
        jsonrpc.request('VideoLibrary.Clean', showdialogs=False)
        self._awaiting = 'VideoLibrary.OnCleanFinished'

    def _sync_changes(self) -> None:
        addon.log("Starting change sync", verbose=True)

        self._update_dialog(32010)

        scan_time = utcdt.now()

        result = jsonrpc.request('VideoLibrary.GetMovies', properties=['file'])
        for movie in result['movies']:
            self._sync_item(media.MediaInfo('movie', movie['movieid'], file=movie['file']))

        result = jsonrpc.request('VideoLibrary.GetTVShows', properties=['file'])
        for tv_show in result['tvshows']:
            self._sync_item(media.MediaInfo('tvshow', tv_show['tvshowid'], file=tv_show['file']))

        result = jsonrpc.request('VideoLibrary.GetEpisodes', properties=['file'])
        for episode in result['episodes']:
            self._sync_item(media.MediaInfo('episode', episode['episodeid'], file=episode['file']))

        last_known.sync_timestamp = scan_time

        self._awaiting = None

    def _sync_item(self, info: media.MediaInfo) -> None:
        should_import = self._item_requires_import(info) if self._should_import else False

        if self._should_export:
            self._export_if_needed(info, should_import)

        if should_import:
            self._import(info)

    def _item_requires_import(self, info: media.MediaInfo) -> bool:
        modification_time = info.nfo_modification_time
        if modification_time is None:
            return False

        last_modification_time = last_known.timestamp(info.type, info.id)
        if last_modification_time is None:
            last_modification_time = self._last_scan

        if modification_time > last_modification_time:
            return True

        return False

    def _import(self, info: media.MediaInfo):
        addon.log(f'Sync - "{info.details["title"]}" has been flagged for import.', verbose=True)
        jsonrpc.request(
            media.TYPE_INFO[info.type].refresh_method,
            **{media.TYPE_INFO[info.type].id_name: info.id}
        )

    def _export_if_needed(self, info: media.MediaInfo, should_import: bool) -> None:
        last_checksum = last_known.checksum(info.type, info.id)

        if last_checksum == info.checksum:
            return
        addon.log(f'Sync - Exporting "{info.details["title"]}" due to checksum difference.')

        overwrite = not should_import if self._should_import_first else None
        success = exporter.export(info=info, overwrite=overwrite)

        if not success:
            self._failures = True

    def _scan(self) -> None:
        addon.log("Starting scan", verbose=True)
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
