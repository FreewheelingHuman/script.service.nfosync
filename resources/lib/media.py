import collections
import zlib
from typing import Final

import resources.lib.jsonrpc as jsonrpc


MediaInfo = collections.namedtuple('MediaInfo', ['details', 'art', 'movieset', 'seasons', 'checksum'])
SeasonInfo = collections.namedtuple('SeasonInfo', ['details', 'art'])

_TypeInfo = collections.namedtuple('TypeInfo', ['method', 'id_name', 'details', 'container'])
_TYPE_INFO: Final = {
    'movieset': _TypeInfo(
        method='VideoLibrary.GetMovieSetDetails',
        id_name='setid',
        details=['title', 'plot'],
        container='setdetails'
    ),
    'movie': _TypeInfo(
        method='VideoLibrary.GetMovieDetails',
        id_name='movieid',
        details=[
            'title', 'genre', 'year', 'director', 'trailer', 'tagline', 'plot',
            'plotoutline', 'originaltitle', 'lastplayed', 'playcount', 'writer',
            'studio', 'mpaa', 'cast', 'country', 'runtime', 'setid', 'showlink',
            'streamdetails', 'top250', 'sorttitle', 'dateadded', 'tag',
            'userrating', 'ratings', 'premiered', 'uniqueid'
        ],
        container='moviedetails',
    ),
    'tvshow': _TypeInfo(
        method='VideoLibrary.GetTVShowDetails',
        id_name='tvshowid',
        details=[
            'title', 'genre', 'year', 'plot', 'studio', 'mpaa', 'cast', 'playcount',
            'episode', 'premiered', 'lastplayed', 'originaltitle',
            'sorttitle', 'season', 'dateadded', 'tag', 'userrating',
            'ratings', 'runtime', 'uniqueid'
        ],
        container='tvshowdetails',
    ),
    'season': _TypeInfo(
        method='VideoLibrary.GetSeasonDetails',
        id_name='seasonid',
        details=['title', 'season'],
        container='seasondetails',
    ),
    'episode': _TypeInfo(
        method='VideoLibrary.GetEpisodeDetails',
        id_name='episodeid',
        details=[
            'title', 'plot', 'writer', 'firstaired', 'playcount', 'runtime',
            'director', 'season', 'episode', 'originaltitle', 'showtitle', 'cast',
            'streamdetails', 'lastplayed', 'dateadded', 'uniqueid',
            'specialsortseason', 'specialsortepisode', 'userrating', 'ratings'
        ],
        container='episodedetails',
    )
}


def file(type_: str, id_: int) -> str:
    type_info = _TYPE_INFO[type_]
    result, raw = jsonrpc.request(
        type_info.method,
        **{type_info.id_name: id_, 'properties': ['file']}
    )
    return result[type_info.container]['file']


def _request_details(type_: str, id_: int) -> (dict, str):
    type_info = _TYPE_INFO[type_]
    result, raw = jsonrpc.request(
        type_info.method,
        **{type_info.id_name: id_, 'properties': type_info.details}
    )
    return result[type_info.container], raw


def _request_art(type_: str, id_: int) -> (dict, str):
    type_info = _TYPE_INFO[type_]
    result, raw = jsonrpc.request(
        'VideoLibrary.GetAvailableArt',
        **{'item': {type_info.id_name: id_}}
    )
    return result['availableart'], raw


def _request_seasons(id_: int) -> (dict, str):
    type_info = _TYPE_INFO['season']
    result, raw = jsonrpc.request(
        'VideoLibrary.GetSeasons',
        **{'tvshowid': id_, 'properties': type_info.details}
    )
    return result['seasons'], raw


def info(type_: str, id_: int) -> MediaInfo:
    checksum_data = []

    details, raw = _request_details(type_, id_)
    checksum_data.append(raw)

    art, raw = _request_art(type_, id_)
    checksum_data.append(raw)

    movieset = None
    seasons = None

    if type_ == 'movie' and details['setid'] != 0:
        movieset, raw = _request_details('movieset', details['setid'])
        checksum_data.append(raw)

    elif type_ == 'tvshow':
        seasons_list, raw = _request_seasons(id_)
        checksum_data.append(raw)

        seasons = {}
        for season in seasons_list:
            season_art, raw = _request_art('season', season['seasonid'])
            seasons[season['season']] = SeasonInfo(details=season, art=season_art)
            checksum_data.append(raw)

    checksum = zlib.crc32(''.join(checksum_data).encode('utf-8'))

    return MediaInfo(
        details=details,
        art=art,
        movieset=movieset,
        seasons=seasons,
        checksum=checksum
    )
