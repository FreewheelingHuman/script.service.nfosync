import collections
import xml.etree.ElementTree as ElementTree
import xbmc
from typing import Callable, Final

import resources.lib.jsonrpc as jsonrpc
from resources.lib.settings import SYNC


class _Exporter:
    _movie_fields: Final = [
        'title', 'genre', 'year', 'director', 'trailer', 'tagline', 'plot',
        'plotoutline', 'originaltitle', 'lastplayed', 'playcount', 'writer',
        'studio', 'mpaa', 'cast', 'country', 'runtime', 'setid', 'showlink',
        'streamdetails', 'top250', 'fanart', 'sorttitle', 'dateadded', 'tag',
        'art', 'userrating', 'ratings', 'premiered', 'uniqueid'
    ]

    _episode_fields: Final = [
        'title', 'plot', 'writer', 'firstaired', 'playcount', 'runtime',
        'director', 'season', 'episode', 'originaltitle', 'showtitle', 'cast',
        'streamdetails', 'lastplayed', 'fanart', 'dateadded', 'uniqueid', 'art',
        'specialsortseason', 'specialsortepisode', 'userrating', 'ratings'
    ]

    _tvshow_fields: Final = [
        'title', 'genre', 'year', 'plot', 'studio', 'mpaa', 'cast', 'playcount',
        'episode', 'premiered', 'lastplayed', 'fanart', 'originaltitle',
        'sorttitle', 'season', 'dateadded', 'tag', 'art', 'userrating',
        'ratings', 'runtime', 'uniqueid'
    ]

    _TypeInfo = collections.namedtuple('_TypeInfo', ['method', 'id_name', 'details', 'container', 'root_tag'])
    _type_info = {
        'movie': _TypeInfo(
            method='VideoLibrary.GetMovieDetails',
            id_name='movieid',
            details=_movie_fields,
            container='moviedetails',
            root_tag='movie'
        ),
        'episode': _TypeInfo(
            method='VideoLibrary.GetEpisodeDetails',
            id_name='episodeid',
            details=_episode_fields,
            container='episodedetails',
            root_tag='episodedetails'
        ),
        'tvshow': _TypeInfo(
            method='VideoLibrary.GetTVShowDetails',
            id_name='tvshowid',
            details=_tvshow_fields,
            container='tvshowdetails',
            root_tag='tvshow'
        )
    }

    # Ignoring label. It always gets returned and is a duplicate to title
    # so far as I can see. However, not sure if it is always the same as
    # title and isn't directly exportable, so rather than mapping label
    # to title and not requesting title, we're ignoring it.
    _ignored_fields = ['label', 'movieid', 'episodeid', 'tvshowid']

    _tag_remaps = {
        'plotoutline': 'outline',
        'writer': 'credits',
        'firstaired': 'aired',
        'specialsortseason': 'displayseason',
        'specialsortepisode': 'displayepisode'
    }

    def __init__(self, media_id: int, media_type: str):
        self._handlers: Final = {
            'art': self._convert_art,
            'cast': self._convert_cast,
            'fanart': self._convert_fanart,
            'ratings': self._convert_ratings,
            'setid': self._convert_set,
            'streamdetails': self._convert_streamdetails,
            'uniqueid': self._convert_uniqueid,
            'trailer': self._conver_trailer
        }

        self._media_id = media_id
        self._media_type = self._type_info[media_type]

        self._xml = ElementTree.Element(self._media_type.root_tag)

    def export(self):
        xbmc.log('PLACEHOLDER: Export has been triggered.')

        parameters = {self._media_type.id_name: self._media_id, 'properties': self._media_type.details}
        result = jsonrpc.request(self._media_type.method, **parameters)

        for field in result[self._media_type.container]:
            handler: Callable[..., None] = self._handlers.get(field, self._convert_generic)
            handler(field, result[self._media_type.container][field])

        self._pretty_print(self._xml)
        xbmc.log(f'Behold! XML:\n{ElementTree.tostring(self._xml, encoding="unicode")}')

    def _pretty_print(self, element, level=1):
        def indent(ilevel):
            return '\n' + '    ' * ilevel

        if len(element):
            if element.text is None or element.text.strip() == '':
                element.text = indent(level)
            for subelement in range(len(element)-1):
                element[subelement].tail = indent(level)
            element[-1].tail = indent(level-1)
            for subelement in element:
                self._pretty_print(subelement, level+1)

    def _convert_generic(self, field: str, value):
        if field in self._ignored_fields:
            return

        if field in self._tag_remaps:
            tag = self._tag_remaps[field]
        else:
            tag = field

        for element in self._xml.findall(tag):
            self._xml.remove(element)

        if value is None or value == '':
            return

        if isinstance(value, list):
            for item in value:
                self._append_tag(self._xml, tag, str(item))
        else:
            self._append_tag(self._xml, tag, str(value))

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

    def _conver_trailer(self, field: str, value):
        xbmc.log(f'convert trailer: {field} with value {value}')

    def _convert_uniqueid(self, field: str, value):
        xbmc.log(f'convert uniqueid: {field} with value {value}')

    def _append_tag(self, parent: ElementTree.Element, tag: str, text: str):
        element = ElementTree.SubElement(parent, tag)
        element.text = text


def export(media_id: int, media_type: str):
    exporter = _Exporter(media_id, media_type)
    exporter.export()
