import datetime
import os

import xbmcgui
import xbmcvfs

from resources.lib.helpers import *


def refresh():
    last_scan = datetime.datetime(1965, 1, 1)

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


def _file_warrants_refresh(file, last_scan):
    if not xbmcvfs.exists(file):
        return False
    stats = xbmcvfs.Stat(file)
    last_modified = datetime.datetime.fromtimestamp(stats.st_mtime())
    if last_modified > last_scan:
        return True
    return False


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
