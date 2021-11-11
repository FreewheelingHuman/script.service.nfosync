import os

import xbmc
import xbmcgui
import xbmcvfs

import resources.lib.utcdt as utcdt
import resources.lib.jsonrpc as jsonrpc
from resources.lib.settings import Settings


class Importer:
    def __init__(self, clean: bool = False, scan: bool = False):
        self._clean = clean
        self._scan = scan
        self._settings = Settings()
        self._running = True

        self._progress_bar = xbmcgui.DialogProgressBG()
        self._progress_bar_up = False

        if self._clean:
            self._update_dialog(32003)
            jsonrpc.request('VideoLibrary.Clean', showdialogs=False)
            return

        self.resume()

    def resume(self):
        self._update_dialog(32010)

        last_scan = self._settings.state.last_refresh
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

        self._settings.state.last_refresh = scan_time

        self._close_dialog()

        if self._scan:
            jsonrpc.request('VideoLibrary.Scan', showdialogs=True)

        self._running = False

    @property
    def running(self):
        return self._running

    def _close_dialog(self):
        if self._progress_bar_up:
            self._progress_bar.close()
            self._progress_bar_up = False

    def _file_warrants_refresh(self, file: str, last_scan: utcdt.Dt) -> bool:
        if not xbmcvfs.exists(file):
            return False

        stats = xbmcvfs.Stat(file)
        last_modified = utcdt.fromtimestamp(stats.st_mtime())

        if last_modified > last_scan:
            return True
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

    def _update_dialog(self, message_num: int):
        heading = xbmc.getLocalizedString(32011)
        message = xbmc.getLocalizedString(message_num)

        if self._progress_bar_up:
            self._progress_bar.update(0, heading, message)
        else:
            self._progress_bar.create(heading, message)
            self._progress_bar_up = True
