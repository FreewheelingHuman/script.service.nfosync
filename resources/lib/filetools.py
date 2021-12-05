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


def create_movie_movie_nfo(media_path: str) -> str:
    return _replace_tail(media_path, 'movie.nfo')


def create_movie_filename_nfo(media_path: str) -> str:
    return replace_extension(media_path, '.nfo')


def get_movie_nfo(media_path: str) -> Optional[str]:
    nfo_path = None
    movie_nfo = create_movie_movie_nfo(media_path)
    filename_nfo = create_movie_filename_nfo(media_path)
    if xbmcvfs.exists(movie_nfo):
        nfo_path = movie_nfo
    elif xbmcvfs.exists(filename_nfo):
        nfo_path = filename_nfo
    return nfo_path


def create_episode_nfo(media_path: str) -> str:
    return replace_extension(media_path, '.nfo')


def get_episode_nfo(media_path: str) -> Optional[str]:
    nfo_path = None
    filename_nfo = create_episode_nfo(media_path)
    if xbmcvfs.exists(filename_nfo):
        nfo_path = filename_nfo
    return nfo_path


def create_tvshow_nfo(media_path: str) -> str:
    return xbmcvfs.validatePath(media_path + '/tvshow.nfo')


def get_tvshow_nfo(media_path: str) -> Optional[str]:
    nfo_path = None
    tvshow_nfo = create_tvshow_nfo(media_path)
    if xbmcvfs.exists(tvshow_nfo):
        nfo_path = tvshow_nfo
    return nfo_path


def get_modification_time(media_path: str) -> Optional[utcdt.UtcDt]:
    result, _ = jsonrpc.request('Files.GetFileDetails', file=media_path, properties=['lastmodified'])
    if result is None:
        return None

    local_iso_timestamp = result['filedetails']['lastmodified']
    dt = utcdt.fromisoformat(local_iso_timestamp)
    return dt


def replace_extension(path: str, extension: str) -> str:
    return os.path.splitext(path)[0] + extension


def _replace_tail(path: str, new_tail: str) -> str:
    return os.path.split(path)[0] + new_tail
