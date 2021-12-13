import os
import urllib.parse
from typing import Final, Optional

import xbmcvfs

import resources.lib.jsonrpc as jsonrpc
import resources.lib.utcdt as utcdt
from resources.lib.addon import addon


def replace_extension(path: str, extension: str) -> str:
    return os.path.splitext(path)[0] + extension


def decode_image(path: str) -> str:
    decoded_path = path.replace('image://', '', 1)
    decoded_path = decoded_path[:-1]
    decoded_path = urllib.parse.unquote(decoded_path)
    return decoded_path


def movie_movie_nfo(path: str) -> str:
    return xbmcvfs.validatePath(os.path.split(path)[0] + '/movie.nfo')


def movie_filename_nfo(path: str) -> str:
    return replace_extension(path, '.nfo')


def tvshow_nfo(path: str) -> str:
    return xbmcvfs.validatePath(path + '/tvshow.nfo')


def episode_nfo(path: str) -> str:
    return replace_extension(path, '.nfo')


def _find_movie_nfo(path: str) -> Optional[str]:
    nfo = None
    movie = movie_movie_nfo(path)
    filename = movie_filename_nfo(path)
    if xbmcvfs.exists(movie):
        nfo = movie
    elif xbmcvfs.exists(filename):
        nfo = filename
    return nfo


def _find_tvshow_nfo(path: str) -> Optional[str]:
    nfo = None
    tvshow = tvshow_nfo(path)
    if xbmcvfs.exists(tvshow):
        nfo = tvshow
    return nfo


def _find_episode_nfo(path: str) -> Optional[str]:
    nfo = None
    filename = episode_nfo(path)
    if xbmcvfs.exists(filename):
        nfo = filename
    return nfo


_nfo_finders: Final = {
    'movie': _find_movie_nfo,
    'tvshow': _find_tvshow_nfo,
    'episode': _find_episode_nfo
}


def find_nfo(type_, path: str) -> Optional[str]:
    return _nfo_finders[type_](path)


def modification_time(path: str) -> Optional[utcdt.UtcDt]:
    try:
        result, _ = jsonrpc.request(
            'Files.GetFileDetails',
            file=path,
            properties=['lastmodified']
        )
        local_iso_timestamp = result['filedetails']['lastmodified']
        return utcdt.fromisoformat(local_iso_timestamp)

    except jsonrpc.RequestError as error:
        addon.log(str(error), verbose=True)
        return None
