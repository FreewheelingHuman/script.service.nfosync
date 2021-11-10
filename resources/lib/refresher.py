import os

import xbmcvfs

import resources.lib.utcdt as utcdt
import resources.lib.jsonrpc as jsonrpc
from resources.lib.settings import Settings


def refresh(clean: bool = False, scan: bool = False, continuation: bool = False) -> None:
    settings = Settings()

    # Prevent multiple refreshes from running simultaneously
    if settings.in_progress.active and not continuation:
        return
    settings.in_progress.active = True

    # In order to let clean finish first, we hop out and then run again
    # without the clean once the monitor sees that the clean is completed.
    if clean:
        settings.in_progress.scan = scan
        jsonrpc.request('VideoLibrary.Clean', showdialogs=False)
        return

    last_scan = settings.state.last_scan
    scan_time = utcdt.now()

    response = jsonrpc.request('VideoLibrary.GetMovies', properties=['file'])
    for movie in response['movies']:
        if _need_refresh_movie(movie['file'], last_scan):
            jsonrpc.request('VideoLibrary.RefreshMovie', movieid=movie['movieid'])

    response = jsonrpc.request('VideoLibrary.GetTVShows', properties=['file'])
    for tv_show in response['tvshows']:
        if _need_refresh_tv_show(tv_show['file'], last_scan):
            jsonrpc.request('VideoLibrary.RefreshTVShow', tvshowid=tv_show['tvshowid'])

    response = jsonrpc.request('VideoLibrary.GetEpisodes', properties=['file'])
    for episode in response['episodes']:
        if _need_refresh_episode(episode['file'], last_scan):
            jsonrpc.request('VideoLibrary.RefreshEpisode', episodeid=episode['episodeid'])

    settings.state.last_scan = scan_time
    settings.in_progress.active = False

    if scan:
        jsonrpc.request('VideoLibrary.Scan', showdialogs=False)


def _file_warrants_refresh(file: str, last_scan: utcdt.Dt) -> bool:
    if not xbmcvfs.exists(file):
        return False

    stats = xbmcvfs.Stat(file)
    last_modified = utcdt.fromtimestamp(stats.st_mtime())

    if last_modified > last_scan:
        return True
    return False


def _need_refresh_episode(file: str, last_scan: utcdt.Dt) -> bool:
    # Ignore missing files
    if not xbmcvfs.exists(file):
        return False

    filename_nfo = os.path.splitext(file)[0] + '.nfo'
    return _file_warrants_refresh(filename_nfo, last_scan)


def _need_refresh_movie(file: str, last_scan: utcdt.Dt) -> bool:
    # Ignore missing files
    if not xbmcvfs.exists(file):
        return False

    if _file_warrants_refresh(file, last_scan):
        return True

    filename_nfo = os.path.splitext(file)[0] + '.nfo'
    if _file_warrants_refresh(filename_nfo, last_scan):
        return True

    movie_nfo = os.path.join(os.path.dirname(file), 'movie.nfo')
    if _file_warrants_refresh(movie_nfo, last_scan):
        return True

    return False


def _need_refresh_tv_show(file: str, last_scan: utcdt.Dt) -> bool:
    # Ignore missing files
    if not xbmcvfs.exists(file):
        return False

    tv_show_nfo = os.path.join(file, 'tvshow.nfo')
    return _file_warrants_refresh(tv_show_nfo, last_scan)
