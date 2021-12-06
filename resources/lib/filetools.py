import os
import urllib.parse
from typing import Optional

import xbmcvfs

import resources.lib.jsonrpc as jsonrpc
import resources.lib.utcdt as utcdt


def decode_image(path: str) -> str:
    decoded_path = path.replace('image://', '', 1)
    decoded_path = decoded_path[:-1]
    decoded_path = urllib.parse.unquote(decoded_path)
    return decoded_path


def movie_movie_nfo(path: str) -> str:
    return _replace_tail(path, 'movie.nfo')


def movie_filename_nfo(path: str) -> str:
    return replace_extension(path, '.nfo')


def find_movie_nfo(path: str) -> Optional[str]:
    nfo = None
    movie = movie_movie_nfo(path)
    filename = movie_filename_nfo(path)
    if xbmcvfs.exists(movie):
        nfo = movie
    elif xbmcvfs.exists(filename):
        nfo = filename
    return nfo


def episode_nfo(path: str) -> str:
    return replace_extension(path, '.nfo')


def find_episode_nfo(path: str) -> Optional[str]:
    nfo = None
    filename = episode_nfo(path)
    if xbmcvfs.exists(filename):
        nfo = filename
    return nfo


def tvshow_nfo(path: str) -> str:
    return xbmcvfs.validatePath(path + '/tvshow.nfo')


def find_tvshow_nfo(path: str) -> Optional[str]:
    nfo = None
    tvshow = tvshow_nfo(path)
    if xbmcvfs.exists(tvshow):
        nfo = tvshow
    return nfo


def modification_time(path: str) -> Optional[utcdt.UtcDt]:
    result, _ = jsonrpc.request(
        'Files.GetFileDetails',
        allow_failure=True,
        file=path,
        properties=['lastmodified']
    )
    if result is None:
        return None

    local_iso_timestamp = result['filedetails']['lastmodified']
    dt = utcdt.fromisoformat(local_iso_timestamp)
    return dt


def replace_extension(path: str, extension: str) -> str:
    return os.path.splitext(path)[0] + extension


def _replace_tail(path: str, tail: str) -> str:
    return os.path.split(path)[0] + tail
