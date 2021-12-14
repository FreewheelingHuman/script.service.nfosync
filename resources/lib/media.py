import os
import collections
import urllib.parse
import zlib
from typing import Optional, Final

import xbmcvfs

import resources.lib.jsonrpc as jsonrpc
import resources.lib.settings as settings
import resources.lib.utcdt as utcdt
from resources.lib.addon import addon


def decode_image(path: str) -> str:
    decoded_path = path.replace('image://', '', 1)
    decoded_path = decoded_path[:-1]
    decoded_path = urllib.parse.unquote(decoded_path)
    return decoded_path


def replace_extension(path: str, extension: str) -> str:
    return os.path.splitext(path)[0] + extension


def _find_modification_time(path: str) -> Optional[utcdt.UtcDt]:
    try:
        result = jsonrpc.request(
            'Files.GetFileDetails',
            file=path,
            properties=['lastmodified']
        )
        local_iso_timestamp = result['filedetails']['lastmodified']
        return utcdt.fromisoformat(local_iso_timestamp)

    except jsonrpc.RequestError as error:
        addon.log(str(error), verbose=True)
        return None


def _movie_movie_nfo(path: str) -> str:
    return xbmcvfs.validatePath(os.path.split(path)[0] + '/movie.nfo')


def _movie_filename_nfo(path: str) -> str:
    return replace_extension(path, '.nfo')


def _find_movie_nfo(path: str) -> (Optional[str], Optional[utcdt.UtcDt]):
    movie = _movie_movie_nfo(path)
    timestamp = _find_modification_time(movie)
    if timestamp is not None:
        return movie, timestamp

    filename = _movie_filename_nfo(path)
    timestamp = _find_modification_time(filename)
    if timestamp is not None:
        return filename, timestamp

    return None, None


def _tvshow_nfo(path: str) -> str:
    return xbmcvfs.validatePath(path + '/tvshow.nfo')


def _find_tvshow_nfo(path: str) -> (Optional[str], Optional[utcdt.UtcDt]):
    nfo = _tvshow_nfo(path)
    timestamp = _find_modification_time(nfo)
    if timestamp is not None:
        return nfo, timestamp
    return None, None


def _episode_nfo(path: str) -> str:
    return replace_extension(path, '.nfo')


def _find_episode_nfo(path: str) -> (Optional[str], Optional[utcdt.UtcDt]):
    nfo = _episode_nfo(path)
    timestamp = _find_modification_time(nfo)
    if timestamp is not None:
        return nfo, timestamp
    return None, None


_TypeInfo = collections.namedtuple('TypeInfo', [
    'details_method',
    'list_method',
    'refresh_method',
    'id_name',
    'details',
    'details_container',
    'list_container',
    'nfo_finder'
])
TYPE_INFO: Final = {
    'movieset': _TypeInfo(
        details_method='VideoLibrary.GetMovieSetDetails',
        list_method='VideoLibrary.GetMovieSets',
        refresh_method=None,
        id_name='setid',
        details=['title', 'plot'],
        details_container='setdetails',
        list_container=None,
        nfo_finder=None
    ),
    'movie': _TypeInfo(
        details_method='VideoLibrary.GetMovieDetails',
        list_method='VideoLibrary.GetMovies',
        refresh_method='VideoLibrary.RefreshMovie',
        id_name='movieid',
        details=[
            'title', 'genre', 'year', 'director', 'trailer', 'tagline', 'plot',
            'plotoutline', 'originaltitle', 'lastplayed', 'playcount', 'writer',
            'studio', 'mpaa', 'cast', 'country', 'runtime', 'setid', 'showlink',
            'streamdetails', 'top250', 'sorttitle', 'dateadded', 'tag',
            'userrating', 'ratings', 'premiered', 'uniqueid'
        ],
        details_container='moviedetails',
        list_container='movies',
        nfo_finder=_find_movie_nfo
    ),
    'tvshow': _TypeInfo(
        details_method='VideoLibrary.GetTVShowDetails',
        list_method='VideoLibrary.GetTVShows',
        refresh_method='VideoLibrary.RefreshTVShow',
        id_name='tvshowid',
        details=[
            'title', 'genre', 'year', 'plot', 'studio', 'mpaa', 'cast', 'playcount',
            'episode', 'premiered', 'lastplayed', 'originaltitle',
            'sorttitle', 'season', 'dateadded', 'tag', 'userrating',
            'ratings', 'runtime', 'uniqueid'
        ],
        details_container='tvshowdetails',
        list_container='tvshows',
        nfo_finder=_find_tvshow_nfo
    ),
    'season': _TypeInfo(
        details_method='VideoLibrary.GetSeasonDetails',
        list_method='VideoLibrary.GetSeasons',
        refresh_method=None,
        id_name='seasonid',
        details=['title', 'season'],
        details_container='seasondetails',
        list_container='seasons',
        nfo_finder=None
    ),
    'episode': _TypeInfo(
        details_method='VideoLibrary.GetEpisodeDetails',
        list_method='VideoLibrary.GetEpisodes',
        refresh_method='VideoLibrary.RefreshEpisode',
        id_name='episodeid',
        details=[
            'title', 'plot', 'writer', 'firstaired', 'playcount', 'runtime',
            'director', 'season', 'episode', 'originaltitle', 'showtitle', 'cast',
            'streamdetails', 'lastplayed', 'dateadded', 'uniqueid',
            'specialsortseason', 'specialsortepisode', 'userrating', 'ratings'
        ],
        details_container='episodedetails',
        list_container='episodes',
        nfo_finder=_find_episode_nfo
    )
}


def get_all(type_: str) -> list:
    type_info = TYPE_INFO[type_]
    result = jsonrpc.request(
        type_info.list_method,
        properties=['file']
    )
    return result[type_info.list_container]


SeasonInfo = collections.namedtuple('SeasonInfo', ['details', 'art'])


class MediaInfo:

    def __init__(self, type_: str, id_: int, file: Optional[str] = None):
        self.type: Final = type_
        self.id: Final = id_

        self._file = file
        self._nfo = ''

        self._details = None
        self._art = None
        self._movieset = None
        self._seasons = None
        self._checksum = None

    @property
    def file(self) -> str:
        if self._file is None:
            type_info = TYPE_INFO[self.type]
            result = jsonrpc.request(
                type_info.details_method,
                **{type_info.id_name: self.id, 'properties': ['file']}
            )
            self._file = result[type_info.details_container]['file']

        return self._file

    @property
    def nfo(self) -> Optional[str]:
        if self._nfo == '':
            self._nfo, _ = TYPE_INFO[self.type].nfo_finder(self.file)

        return self._nfo

    @property
    def nfo_modification_time(self) -> Optional[utcdt.UtcDt]:
        if self._nfo is None:
            return None
        elif self._nfo == '':
            self._nfo, modification_time = TYPE_INFO[self.type].nfo_finder(self.file)
            return modification_time
        else:
            return _find_modification_time(self._nfo)

    @property
    def details(self) -> dict:
        if self._details is None:
            self._details = self._request_details(self.type, self.id)

        return self._details

    @property
    def art(self) -> dict:
        if self._art is None:
            self._art = self._request_art(self.type, self.id)

        return self._art

    @property
    def movieset(self) -> dict:
        if self._movieset is None:
            if self.type != 'movie' or self.details['setid'] == 0:
                self._movieset = {}
            else:
                self._movieset = self._request_details('movieset', self.details['setid'])

        return self._movieset

    @property
    def seasons(self) -> dict:
        if self._seasons is None:
            self._seasons = {}
            if self.type == 'tvshow':
                type_info = TYPE_INFO['season']
                result = jsonrpc.request(
                    type_info.list_method,
                    **{'tvshowid': self.id, 'properties': type_info.details}
                )
                seasons = result[type_info.list_container]
                for season in seasons:
                    art = self._request_art('season', self.id)
                    self._seasons[season['season']] = SeasonInfo(details=season, art=art)

        return self._seasons

    @property
    def checksum(self) -> int:
        if self._checksum is None:
            checksum = zlib.crc32(str(self.details).encode('utf-8'))
            checksum = zlib.crc32(str(self.art).encode('utf-8'), checksum)
            checksum = zlib.crc32(str(self.movieset).encode('utf-8'), checksum)
            self._checksum = zlib.crc32(str(self.seasons).encode('utf-8'), checksum)

        return self._checksum

    def create_nfo_path(self):
        if self.type == 'movie':
            if settings.export.movie_nfo_naming == settings.MovieNfoOption.MOVIE:
                self._nfo = _movie_movie_nfo(self._file)
            else:
                self._nfo = _movie_filename_nfo(self._file)

        if self.type == 'episode':
            self._nfo = _episode_nfo(self._file)

        if self.type == 'tvshow':
            self._nfo = _tvshow_nfo(self._file)

    def _request_art(self, type_: str, id_: int):
        type_info = TYPE_INFO[type_]
        result = jsonrpc.request(
            'VideoLibrary.GetAvailableArt',
            **{'item': {type_info.id_name: id_}}
        )
        return result['availableart']

    def _request_details(self, type_: str, id_: int) -> dict:
        type_info = TYPE_INFO[type_]
        result = jsonrpc.request(
            type_info.details_method,
            **{type_info.id_name: id_, 'properties': type_info.details}
        )
        return result[type_info.details_container]
