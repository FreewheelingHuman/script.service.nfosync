import os
import urllib.parse
from typing import Optional

import xbmcvfs


def decode_image(path: str) -> str:
    decoded_path = path.replace('image://', '', 1)
    decoded_path = urllib.parse.unquote(decoded_path)
    return decoded_path


def get_movie_nfo(media_path: str) -> Optional[str]:
    nfo_path = None
    movie_nfo = _replace_tail(media_path, 'movie.nfo')
    filename_nfo = _replace_extension(media_path, '.nfo')
    if xbmcvfs.exists(movie_nfo):
        nfo_path = movie_nfo
    elif xbmcvfs.exists(filename_nfo):
        nfo_path = filename_nfo
    return nfo_path


def get_episode_nfo(media_path: str) -> Optional[str]:
    nfo_path = None
    filename_nfo = _replace_extension(media_path, '.nfo')
    if xbmcvfs.exists(filename_nfo):
        nfo_path = filename_nfo
    return nfo_path


def get_tvshow_nfo(media_path: str) -> Optional[str]:
    nfo_path = None
    tvshow_nfo = xbmcvfs.validatePath(media_path + '/tvshow.nfo')
    if xbmcvfs.exists(tvshow_nfo):
        nfo_path = tvshow_nfo
    return nfo_path


def _replace_extension(path: str, extension: str) -> str:
    return os.path.splitext(path)[0] + extension


def _replace_tail(path: str, new_tail: str) -> str:
    return os.path.split(path)[0] + new_tail
