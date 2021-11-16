import collections
import xml.etree.ElementTree as ElementTree
import xbmc
from typing import Callable, Final

import resources.lib.jsonrpc as jsonrpc
from resources.lib.addon import SETTINGS


class _Exporter:
    _movie_details: Final = [
        'title', 'genre', 'year', 'director', 'trailer', 'tagline', 'plot',
        'plotoutline', 'originaltitle', 'lastplayed', 'playcount', 'writer',
        'studio', 'mpaa', 'cast', 'country', 'runtime', 'setid', 'showlink',
        'streamdetails', 'top250', 'fanart', 'sorttitle', 'dateadded', 'tag',
        'art', 'userrating', 'ratings', 'premiered', 'uniqueid'
    ]

    _episode_details: Final = [
        'title', 'plot', 'writer', 'firstaired', 'playcount', 'runtime',
        'director', 'season', 'episode', 'originaltitle', 'showtitle', 'cast',
        'streamdetails', 'lastplayed', 'fanart', 'dateadded', 'uniqueid', 'art',
        'specialsortseason', 'specialsortepisode', 'userrating', 'ratings'
    ]

    _tvshow_details: Final = [
        'title', 'genre', 'year', 'plot', 'studio', 'mpaa', 'cast', 'playcount',
        'episode', 'premiered', 'lastplayed', 'fanart', 'originaltitle',
        'sorttitle', 'season', 'dateadded', 'tag', 'art', 'userrating',
        'ratings', 'runtime', 'uniqueid'
    ]

    _TypeInfo = collections.namedtuple('_TypeInfo', ['method', 'id_name', 'details', 'container'])
    _type_info = {
        'movie': _TypeInfo(
            method='VideoLibrary.GetMovieDetails',
            id_name='movieid',
            details=_movie_details,
            container='moviedetails'
        ),
        'episode': _TypeInfo(
            method='VideoLibrary.GetEpisodeDetails',
            id_name='episodeid',
            details=_episode_details,
            container='episodedetails'
        ),
        'tvshow': _TypeInfo(
            method='VideoLibrary.GetTVShowDetails',
            id_name='tvshowid',
            details=_tvshow_details,
            container='tvshowdetails'
        )
    }

    _tag_remaps = {
        'plotoutline': 'outline',
        'writer': 'credits',
        'firstaired': 'aired',
        'specialsortseason': 'displayseason',
        'specialsortepisode': 'displayepisode'
    }

    def __init__(self, media_id: int, media_type: str):
        self._media_id = media_id
        self._media_type = media_type

        self._handlers: Final = {
            'art': self._convert_art,
            'cast': self._convert_cast,
            'fanart': self._convert_fanart,
            'ratings': self._convert_ratings,
            'setid': self._convert_set,
            'streamdetails': self._convert_streamdetails,
            'uniqueid': self._convert_uniqueid
        }

    def export(self):
        xbmc.log('PLACEHOLDER: Export has been triggered.')

        type_info = self._type_info[self._media_type]
        parameters = {type_info.id_name: self._media_id, 'properties': type_info.details}
        result = jsonrpc.request(type_info.method, **parameters)

        for field in result[type_info.container]:
            handler: Callable[..., None] = self._handlers.get(field, self._convert_generic)
            handler(field, result[type_info.container][field])

    def _pretty_print(self, element, level=1):
        def indent(ilevel):
            return '\n' + '    ' * ilevel

        if len(element):
            if element.text is None:
                element.text = indent(level)
            for subelement in range(len(element)-1):
                element[subelement].tail = indent(level)
            element[-1].tail = indent(level-1)
            for subelement in element:
                self._pretty_print(subelement, level+1)

    def _convert_generic(self, field: str, value):
        xbmc.log(f'convert generic: {field} with value {value}')

    def _convert_art(self, field: str, value):
        xbmc.log(f'convert art: {field} with value {value}')

    def _convert_cast(self, field: str, value):
        xbmc.log(f'convert cast: {field} with value {value}')

    def _convert_fanart(self, field: str, value):
        xbmc.log(f'convert fanart: {field} with value {value}')

    def _convert_ratings(self, field: str, value):
        xbmc.log(f'convert ratings: {field} with value {value}')

    def _convert_set(self, field: str, value):
        xbmc.log(f'convert set: {field} with value {value}')

    def _convert_streamdetails(self, field: str, value):
        xbmc.log(f'convert streamdetails: {field} with value {value}')

    def _convert_uniqueid(self, field: str, value):
        xbmc.log(f'convert uniqueid: {field} with value {value}')


def export(media_id: int, media_type: str):
    exporter = _Exporter(media_id, media_type)
    exporter.export()
