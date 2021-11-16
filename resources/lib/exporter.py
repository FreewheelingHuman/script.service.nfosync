import xml.etree.ElementTree as ElementTree
import xbmc

import resources.lib.jsonrpc as jsonrpc
from resources.lib.addon import SETTINGS


class _Exporter:
    _movie_details = [
        'title', 'genre', 'year', 'director', 'trailer', 'tagline', 'plot',
        'plotoutline', 'originaltitle', 'lastplayed', 'playcount', 'writer',
        'studio', 'mpaa', 'cast', 'country', 'runtime', 'setid', 'showlink',
        'streamdetails', 'top250', 'fanart', 'sorttitle', 'dateadded', 'tag',
        'art', 'userrating', 'ratings', 'premiered', 'uniqueid'
    ]

    _episode_details = [
        'title', 'plot', 'writer', 'firstaired', 'playcount', 'runtime',
        'director', 'season', 'episode', 'originaltitle', 'showtitle', 'cast',
        'streamdetails', 'lastplayed', 'fanart', 'dateadded', 'uniqueid', 'art',
        'specialsortseason', 'specialsortepisode', 'userrating', 'ratings'
    ]

    _tvshow_details = [
        'title', 'genre', 'year', 'plot', 'studio', 'mpaa', 'cast', 'playcount',
        'episode', 'premiered', 'lastplayed', 'fanart', 'originaltitle',
        'sorttitle', 'season', 'dateadded', 'tag', 'art', 'userrating',
        'ratings', 'runtime', 'uniqueid'
    ]

    _remappings = {
        'plotoutline': 'outline',
        'writer': 'credits',
        'firstaired': 'aired',
        'specialsortseason': 'displayseason',
        'specialsortepisode': 'displayepisode'
    }

    def __init__(self, media_id: int, media_type: str):
        self._media_id = media_id
        self._media_type = media_type

        self._handlers = {
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

        result = jsonrpc.request(
            'VideoLibrary.GetMovieDetails',
            movieid=self._media_id,
            properties=self._movie_details
        )
        xbmc.log(f'Results: {result}')

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

    def _convert_art(self):
        pass

    def _convert_cast(self):
        pass

    def _convert_fanart(self):
        pass

    def _convert_ratings(self):
        pass

    def _convert_set(self):
        pass

    def _convert_streamdetails(self):
        pass

    def _convert_uniqueid(self):
        pass


def export(media_id: int, media_type: str):
    exporter = _Exporter(media_id, media_type)
    exporter.export()
