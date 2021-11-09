import datetime
import json
import os

import xbmc
import xbmcaddon
import xbmcvfs


def refresh(clean=False):
    addon = xbmcaddon.Addon()

    # Prevent multiple refreshes from running simultaneously
    if addon.getSettingBool('in_progress.active'):
        return
    addon.setSettingBool('in_progress.active', True)

    # In order to let clean finish first, we hop out and then run again
    # without the clean once the monitor sees that the clean is completed.
    if clean:
        _jsonrpc('VideoLibrary.Clean', showdialogs=False)
        return

    last_scan = datetime.datetime.fromisoformat(addon.getSetting('state.last_scan'))
    scan_time = datetime.datetime.now(datetime.timezone.utc)

    movies = _jsonrpc('VideoLibrary.GetMovies', properties=['file'])['movies']
    for movie in movies:
        if _need_refresh_movie(movie['file'], last_scan):
            _jsonrpc('VideoLibrary.RefreshMovie', movieid=movie['movieid'])

    tv_shows = _jsonrpc('VideoLibrary.GetTVShows', properties=['file'])['tvshows']
    for tv_show in tv_shows:
        if _need_refresh_tv_show(tv_show['file'], last_scan):
            _jsonrpc('VideoLibrary.RefreshTVShow', tvshowid=tv_show['tvshowid'])

    episodes = _jsonrpc('VideoLibrary.GetEpisodes', properties=['file'])['episodes']
    for episode in episodes:
        if _need_refresh_episode(episode['file'], last_scan):
            _jsonrpc('VideoLibrary.RefreshEpisode', episodeid=episode['episodeid'])

    addon.setSetting('state.last_scan', scan_time.isoformat(timespec='seconds'))
    addon.setSettingBool('in_progress.active', False)


def _file_warrants_refresh(file, last_scan):
    if not xbmcvfs.exists(file):
        return False
    stats = xbmcvfs.Stat(file)
    last_modified = datetime.datetime.fromtimestamp(stats.st_mtime(), datetime.timezone.utc)
    if last_modified > last_scan:
        return True
    return False


def _jsonrpc(method, **params):
    request = {
        'jsonrpc': '2.0',
        'method': method,
        'params': params,
        'id': 1
    }
    result = xbmc.executeJSONRPC(json.dumps(request))
    return json.loads(result)['result']


def _need_refresh_episode(file, last_scan):
    # Ignore missing files
    if not xbmcvfs.exists(file):
        return False

    filename_nfo = os.path.splitext(file)[0] + '.nfo'
    return _file_warrants_refresh(filename_nfo, last_scan)


def _need_refresh_movie(file, last_scan):
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


def _need_refresh_tv_show(file, last_scan):
    # Ignore missing files
    if not xbmcvfs.exists(file):
        return False

    tv_show_nfo = os.path.join(file, 'tvshow.nfo')
    return _file_warrants_refresh(tv_show_nfo, last_scan)
