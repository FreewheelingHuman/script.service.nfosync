import collections
from typing import Final

import xbmcgui

import resources.lib.jsonrpc as jsonrpc
import resources.lib.media as media
import resources.lib.settings as settings
import resources.lib.utcdt as utcdt
from resources.lib.addon import addon
from resources.lib.last_known import last_known
from resources.lib.timestamps import timestamps


from . import *


def _item_requires_import(info: media.MediaInfo) -> bool:
    modification_time = info.nfo_modification_time()
    if modification_time is None:
        return False

    last_modification_time = last_known.timestamp(info.type, info.id)
    if last_modification_time is None:
        last_modification_time = timestamps.last_sync

    if modification_time > last_modification_time:
        return True

    return False


def _item_requires_export(info: media.MediaInfo) -> bool:
    last_checksum = last_known.checksum(info.type, info.id)

    if last_checksum == info.checksum:
        return False

    return True


def _sync_item(info: media.MediaInfo) -> None:
    should_import = _item_requires_import(info)
    should_export = _item_requires_export(info)

    if should_export:
        overwrite = not should_import if settings.sync.should_import_first else None
        ExportOne(info, overwrite=overwrite, subtask=True).run()

    if should_import:
        ImportOne(info).run()


class SyncOne(Action):

    _type = 'Sync One'

    def __init__(self, info: media.MediaInfo):
        super().__init__()
        self._info = info

    def run(self) -> None:
        _sync_item(self._info)
        # if sync._failures:
        #    addon.notify(32064)


class SyncAll(Action):

    _type = 'Sync All'
    _progress_bar: Final = xbmcgui.DialogProgressBG()

    def __init__(self, should_skip_scan: bool = False):
        super().__init__()

        # Create a local copy of all settings in case they change mid-sync
        self._should_clean = settings.sync.should_clean
        self._should_import = settings.sync.should_import
        self._should_import_first = settings.sync.should_import_first
        self._should_export = settings.sync.should_export
        self._should_scan = settings.sync.should_scan

        self._stages = collections.deque()
        if self._should_clean:
            self._stages.append(self._clean)
        if self._should_import or self._should_export:
            self._stages.append(self._sync_changes)
        if self._scan and not should_skip_scan:
            self._stages.append(self._scan)
        self._stage_count = len(self._stages)

        self._should_show = settings.ui.should_show_sync
        self._progress_bar_up = False

        self._failures = False

    def run(self) -> None:
        while self._stages:
            self._stages[0]()
            self._stages.popleft()
            if self._awaiting:
                return

        self._close_dialog()

        if self._failures:
            addon.notify(32064)

        return

    def _clean(self) -> None:
        self._update_dialog(32003)
        jsonrpc.request('VideoLibrary.Clean', showdialogs=False)
        self._awaiting = 'VideoLibrary.OnCleanFinished'

    def _sync_changes(self) -> None:
        self._update_dialog(32010)

        scan_time = utcdt.now()

        for movie in media.get_all('movie'):
            _sync_item(media.MediaInfo('movie', movie['movieid'], file=movie['file']))

        for tvshow in media.get_all('tvshow'):
            _sync_item(media.MediaInfo('tvshow', tvshow['tvshowid'], file=tvshow['file']))

        for episode in media.get_all('episode'):
            _sync_item(media.MediaInfo('episode', episode['episodeid'], file=episode['file']))

        timestamps.last_sync = scan_time

        self._awaiting = None

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
