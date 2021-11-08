import datetime
import json
import os

import xbmcaddon
import xbmcgui
import xbmcvfs

from resources.lib.helpers import *


def refresh():
    profile_folder = xbmcaddon.Addon().getAddonInfo('profile')
    state_file = xbmcvfs.translatePath(f'{profile_folder}/state.json')
    last_scan = _get_last_scan(state_file)
    scan_time = datetime.datetime.now()

    movies = jsonrpc('VideoLibrary.GetMovies', properties=['file'])['movies']
    for movie in movies:
        if _need_refresh_movie(movie['file'], last_scan):
            jsonrpc('VideoLibrary.RefreshMovie', movieid=movie['movieid'])

    tv_shows = jsonrpc('VideoLibrary.GetTVShows', properties=['file'])['tvshows']
    for tv_show in tv_shows:
        if _need_refresh_tv_show(tv_show['file'], last_scan):
            jsonrpc('VideoLibrary.RefreshTVShow', tvshowid=tv_show['tvshowid'])

    episodes = jsonrpc('VideoLibrary.GetEpisodes', properties=['file'])['episodes']
    for episode in episodes:
        if _need_refresh_episode(episode['file'], last_scan):
            jsonrpc('VideoLibrary.RefreshEpisode', episodeid=episode['episodeid'])

    _update_last_scan(state_file, scan_time)


def _file_warrants_refresh(file, last_scan):
    if not xbmcvfs.exists(file):
        return False
    stats = xbmcvfs.Stat(file)
    last_modified = datetime.datetime.fromtimestamp(stats.st_mtime())
    if last_modified > last_scan:
        return True
    return False


def _get_last_scan(state_file):
    if not xbmcvfs.exists(state_file):
        return datetime.datetime.now()

    with xbmcvfs.File(state_file) as file:
        state = json.loads(file.read())

    return datetime.datetime.fromtimestamp(state['last_scan'])


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


def _update_last_scan(state_file, scan_time):
    state = {'last_scan': scan_time.timestamp()}

    xbmcvfs.mkdirs(os.path.dirname(state_file))
    with xbmcvfs.File(state_file, 'w') as file:
        file.write(json.dumps(state))
