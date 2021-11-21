import os
from typing import Final

import xbmc
import xbmcgui
import xbmcvfs

import resources.lib.utcdt as utcdt
import resources.lib.jsonrpc as jsonrpc
from resources.lib.addon import ADDON
from resources.lib.settings import SYNC, STATE


class Sync:
    _progress_bar: Final = xbmcgui.DialogProgressBG()

    def __init__(self):
        self._todo_clean = SYNC.clean
        self._todo_imprt = SYNC.imprt
        self._todo_scan = SYNC.scan
        self._visible = SYNC.visible

        self._progress_bar_up = False

        self._awaiting = ''

        self._stages: Final = [self._todo_clean, self._todo_imprt, self._todo_scan].count(True)

    @property
    def awaiting(self) -> str:
        return self._awaiting

    # Returns true when it is done
    def resume(self) -> bool:
        if self._todo_clean:
            self._update_dialog(32003)
            self._todo_clean = False
            self._clean()
            self._awaiting = 'VideoLibrary.OnCleanFinished'
            return False

        if self._todo_imprt:
            self._update_dialog(32010)
            self._todo_imprt = False
            self._refresh()
            self._awaiting = ''

        if self._todo_scan:
            self._update_dialog(32012)
            self._todo_scan = False
            self._scan()
            self._awaiting = 'VideoLibrary.OnScanFinished'
            return False

        self._close_dialog()
        return True

    @classmethod
    def start(cls) -> ('Sync', bool):
        importer = cls()
        return importer, importer.resume()

    @staticmethod
    def _clean() -> None:
        jsonrpc.request('VideoLibrary.Clean', showdialogs=False)

    def _refresh(self) -> None:
        last_scan = STATE.last_refresh
        scan_time = utcdt.now()

        response = jsonrpc.request('VideoLibrary.GetMovies', properties=['file'])
        for movie in response['movies']:
            if self._need_refresh_movie(movie['file'], last_scan):
                jsonrpc.request('VideoLibrary.RefreshMovie', movieid=movie['movieid'])

        response = jsonrpc.request('VideoLibrary.GetTVShows', properties=['file'])
        for tv_show in response['tvshows']:
            if self._need_refresh_tv_show(tv_show['file'], last_scan):
                jsonrpc.request('VideoLibrary.RefreshTVShow', tvshowid=tv_show['tvshowid'])

        response = jsonrpc.request('VideoLibrary.GetEpisodes', properties=['file'])
        for episode in response['episodes']:
            if self._need_refresh_episode(episode['file'], last_scan):
                jsonrpc.request('VideoLibrary.RefreshEpisode', episodeid=episode['episodeid'])

        STATE.last_refresh = scan_time

    @staticmethod
    def _scan() -> None:
        jsonrpc.request('VideoLibrary.Scan', showdialogs=False)

    @staticmethod
    def _file_warrants_refresh(file: str, last_scan: utcdt.Dt) -> bool:
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
            xbmc.log(f'Unable to check timestamp of "{file}" due to: {error}')

        return False

    def _need_refresh_episode(self, file: str, last_scan: utcdt.Dt) -> bool:
        # Ignore missing files
        if not xbmcvfs.exists(file):
            return False

        filename_nfo = os.path.splitext(file)[0] + '.nfo'
        return self._file_warrants_refresh(filename_nfo, last_scan)

    def _need_refresh_movie(self, file: str, last_scan: utcdt.Dt) -> bool:
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

    def _need_refresh_tv_show(self, file: str, last_scan: utcdt.Dt) -> bool:
        # Ignore missing files
        if not xbmcvfs.exists(file):
            return False

        tv_show_nfo = os.path.join(file, 'tvshow.nfo')
        return self._file_warrants_refresh(tv_show_nfo, last_scan)

    def _close_dialog(self) -> None:
        if not self._visible:
            return

        if self._progress_bar_up:
            self._progress_bar.close()
            self._progress_bar_up = False

    def _update_dialog(self, message_num: int) -> None:
        if not self._visible:
            return

        heading = ADDON.getLocalizedString(32011)
        message = ADDON.getLocalizedString(message_num)

        if self._progress_bar_up:
            stages_to_go = [self._todo_clean, self._todo_imprt, self._todo_scan].count(True)
            progress = int((1 - (stages_to_go / self._stages)) * 100)
            self._progress_bar.update(progress, heading, message)
        else:
            self._progress_bar.create(heading, message)
            self._progress_bar_up = True
