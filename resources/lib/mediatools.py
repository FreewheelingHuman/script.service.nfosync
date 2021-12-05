import collections
from typing import Final

import resources.lib.jsonrpc as jsonrpc


_TypeInfo = collections.namedtuple('TypeInfo', ['method', 'id_name', 'details', 'container'])
TYPE_INFO: Final = {
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


def get_file(media_type_name: str, media_id: int) -> (dict, str):
    media_type = TYPE_INFO[media_type_name]
    result, raw = jsonrpc.request(
        media_type.method,
        **{media_type.id_name: media_id, 'properties': ['file']}
    )
    return result[media_type.container]['file'], raw


def get_details(media_type_name: str, media_id: int) -> (dict, str):
    media_type = TYPE_INFO[media_type_name]
    result, raw = jsonrpc.request(
        media_type.method,
        **{media_type.id_name: media_id, 'properties': media_type.details}
    )
    return result[media_type.container], raw


def get_art(media_type_name: str, media_id: int) -> (dict, str):
    media_type = TYPE_INFO[media_type_name]
    result, raw = jsonrpc.request(
        'VideoLibrary.GetAvailableArt',
        **{'item': {media_type.id_name: media_id}}
    )
    return result['availableart'], raw


def get_seasons(media_id: int) -> (dict, str):
    media_type = TYPE_INFO['season']
    result, raw = jsonrpc.request(
        'VideoLibrary.GetSeasons',
        **{'tvshowid': media_id, 'properties': media_type.details}
    )
    return result['seasons'], raw
