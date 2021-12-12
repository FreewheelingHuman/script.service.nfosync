import os
from collections import deque
from typing import Final

import xbmcgui
import xbmcvfs

import resources.lib.utcdt as utcdt
import resources.lib.jsonrpc as jsonrpc
import resources.lib.settings as settings
from resources.lib.addon import addon
from resources.lib.last_known import last_known


class Sync:
    _progress_bar: Final = xbmcgui.DialogProgressBG()

    def __init__(self):
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
        if self._scan:
            self._stages.append(self._scan)
        self._stage_count = len(self._stages)

        self._should_show = settings.ui.should_show_sync
        self._progress_bar_up = False
        self._awaiting = None

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

        self._close_dialog()
        return True

    @classmethod
    def start(cls) -> ('Sync', bool):
        sync = cls()
        return sync, sync.resume()

    def _clean(self) -> None:
        addon.log("Starting clean", verbose=True)
        self._update_dialog(32003)
        jsonrpc.request('VideoLibrary.Clean', showdialogs=False)
        self._awaiting = 'VideoLibrary.OnCleanFinished'

    def _sync_changes(self) -> None:
        addon.log("Starting change sync", verbose=True)

        self._update_dialog(32010)

        last_scan = last_known.sync_timestamp
        scan_time = utcdt.now()

        result, _ = jsonrpc.request('VideoLibrary.GetMovies', properties=['file'])
        for movie in result['movies']:
            if self._need_refresh_movie(movie['file'], last_scan):
                jsonrpc.request('VideoLibrary.RefreshMovie', movieid=movie['movieid'])

        result, _ = jsonrpc.request('VideoLibrary.GetTVShows', properties=['file'])
        for tv_show in result['tvshows']:
            if self._need_refresh_tv_show(tv_show['file'], last_scan):
                jsonrpc.request('VideoLibrary.RefreshTVShow', tvshowid=tv_show['tvshowid'])

        result, _ = jsonrpc.request('VideoLibrary.GetEpisodes', properties=['file'])
        for episode in result['episodes']:
            if self._need_refresh_episode(episode['file'], last_scan):
                jsonrpc.request('VideoLibrary.RefreshEpisode', episodeid=episode['episodeid'])

        last_known.sync_timestamp = scan_time

        self._awaiting = None

    def _scan(self) -> None:
        addon.log("Starting scan", verbose=True)
        self._update_dialog(32012)
        jsonrpc.request('VideoLibrary.Scan', showdialogs=False)
        self._awaiting = 'VideoLibrary.OnScanFinished'

    def _file_warrants_refresh(self, file: str, last_scan: utcdt.UtcDt) -> bool:
        if not xbmcvfs.exists(file):
            return False

        stats = xbmcvfs.Stat(file)

        # Stat doesn't give any indication if it was successful.
        # If it failed, then st_mtime will be random garbage.
        # If this happens to be a valid POSIX timestamp, then we get an erroneous result, unfortunately.
        # If it isn't a valid POSIX timestamp, we get an exception we can at least handle
        try:
            last_modified = utcdt.fromtimestamp(stats.st_mtime())
            if last_modified > last_scan:
                return True

        except (OSError, OverflowError) as error:
            addon.log(f'Unable to check timestamp of "{file}" due to: {error}')

        return False

    def _need_refresh_episode(self, file: str, last_scan: utcdt.UtcDt) -> bool:
        # Ignore missing files
        if not xbmcvfs.exists(file):
            return False

        filename_nfo = os.path.splitext(file)[0] + '.nfo'
        return self._file_warrants_refresh(filename_nfo, last_scan)

    def _need_refresh_movie(self, file: str, last_scan: utcdt.UtcDt) -> bool:
        # Ignore missing files
        if not xbmcvfs.exists(file):
            return False

        if self._file_warrants_refresh(file, last_scan):
            return True

        filename_nfo = os.path.splitext(file)[0] + '.nfo'
        if self._file_warrants_refresh(filename_nfo, last_scan):
            return True

        movie_nfo = os.path.join(os.path.dirname(file), 'movie.nfo')
        if self._file_warrants_refresh(movie_nfo, last_scan):
            return True

        return False

    def _need_refresh_tv_show(self, file: str, last_scan: utcdt.UtcDt) -> bool:
        # Ignore missing files
        if not xbmcvfs.exists(file):
            return False

        tv_show_nfo = os.path.join(file, 'tvshow.nfo')
        return self._file_warrants_refresh(tv_show_nfo, last_scan)

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
