import collections
import os
import urllib.parse
import xml.etree.ElementTree as ElementTree
import xbmc
from typing import Callable, Final

import xbmcvfs

import resources.lib.jsonrpc as jsonrpc
from resources.lib.addon import ADDON
from resources.lib.settings import SYNC, ActorTagOption


class _ExportFailure(Exception):
    pass


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
    _ignored_fields = ['label', 'file', 'movieid', 'episodeid', 'tvshowid']

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

        self._file = None
        self._xml = None

    def export(self) -> None:
        xbmc.log('PLACEHOLDER: Export has been triggered.')

        parameters = {self._media_type.id_name: self._media_id, 'properties': ['file']}
        details = jsonrpc.request(self._media_type.method, **parameters)[self._media_type.container]
        self._file = details['file']
        self._import_nfo(self._file)
        if self._xml is None:
            if SYNC.create_nfo:
                self._xml = ElementTree.Element(self._media_type.root_tag)
            else:
                return

        parameters = {self._media_type.id_name: self._media_id, 'properties': self._media_type.details}
        details = jsonrpc.request(self._media_type.method, **parameters)[self._media_type.container]
        xbmc.log(f'Source JSON:\n{details}')
        for field in details:
            handler: Callable[..., None] = self._handlers.get(field, self._convert_generic)
            handler(field, details[field])

        self._pretty_print(self._xml)
        xbmc.log(f'Behold! XML:\n{ElementTree.tostring(self._xml, encoding="unicode")}')

    def _pretty_print(self, element, level=1) -> None:
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

    def _convert_generic(self, field: str, value) -> None:
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
                self._add_tag(self._xml, tag, item)
        else:
            self._add_tag(self._xml, tag, value)

    def _convert_art(self, field: str, value) -> None:
        xbmc.log(f'convert art: {field} with value {value}')

    def _convert_cast(self, field: str, actors) -> None:
        actor_bin = ElementTree.Element('bucket')
        existing_actors = self._xml.findall('actor')

        if existing_actors and SYNC.actor == ActorTagOption.SKIP:
            return

        if SYNC.actor != ActorTagOption.OVERWRITE:
            actor_bin.extend(existing_actors)

        for actor in existing_actors:
            self._xml.remove(actor)

        if SYNC.actor == ActorTagOption.UPDATE:
            self._update_cast(actors, actor_bin)
        else:
            self._merge_cast(actors, actor_bin)

    def _convert_fanart(self, field: str, value) -> None:
        xbmc.log(f'convert fanart: {field} with value {value}')

    def _convert_ratings(self, field: str, value) -> None:
        xbmc.log(f'convert ratings: {field} with value {value}')

    def _convert_set(self, field: str, value) -> None:
        xbmc.log(f'convert set: {field} with value {value}')

    def _convert_streamdetails(self, field: str, value) -> None:
        xbmc.log(f'convert streamdetails: {field} with value {value}')

    def _conver_trailer(self, field: str, value) -> None:
        xbmc.log(f'convert trailer: {field} with value {value}')

    def _convert_uniqueid(self, field: str, value) -> None:
        xbmc.log(f'convert uniqueid: {field} with value {value}')

    def _update_cast(self, new_actors: list, old_actors: ElementTree.Element):
        for element in old_actors:
            self._xml.append(element)
            actor_name = element.find('name').text
            details = next((a for a in new_actors if a['name'] == actor_name), None)
            if details is not None:
                self._update_actor(element, details)

    def _merge_cast(self, new_actors: list, old_actors: ElementTree.Element):
        for actor in new_actors:
            element = old_actors.find(f'*/[name=\'{actor["name"]}\']')
            if element is None:
                element = self._add_tag(self._xml, 'actor')
            else:
                self._xml.append(element)
            self._update_actor(element, actor)

    def _update_actor(self, element, details) -> None:
        if 'name' in details:
            self._set_tag(element, 'name', details['name'])
        if 'role' in details:
            self._set_tag(element, 'role', details['role'])
        if 'order' in details:
            self._set_tag(element, 'order', details['order'])
        if 'thumbnail' in details:
            self._set_tag(element, 'thumb', self._decode_image(details['thumbnail']))

    def _add_tag(self, parent: ElementTree.Element, tag: str, text: str = None) -> ElementTree.Element:
        element = ElementTree.SubElement(parent, tag)
        if text is not None:
            element.text = str(text)
        return element

    def _set_tag(self, parent: ElementTree.Element, tag: str, text: str) -> ElementTree.Element:
        element = parent.find(tag)
        if element is None:
            element = self._add_tag(parent, tag, text)
        else:
            element.text = str(text)
        return element

    def _import_nfo(self, media_path: str) -> None:
        if media_path is None or media_path == '':
            raise _ExportFailure(f'Empty media path for library id "{self._media_id}"')

        nfo_path = None

        if self._media_type == self._type_info['movie']:
            movie_nfo = self._replace_tail(media_path, 'movie.nfo')
            filename_nfo = self._replace_extension(media_path, '.nfo')
            if xbmcvfs.exists(movie_nfo):
                nfo_path = movie_nfo
            elif xbmcvfs.exists(filename_nfo):
                nfo_path = filename_nfo

        elif self._media_type == self._type_info['episode']:
            filename_nfo = self._replace_extension(media_path, '.nfo')
            if xbmcvfs.exists(filename_nfo):
                nfo_path = filename_nfo

        elif self._media_type == self._type_info['tvshow']:
            tvshow_nfo = xbmcvfs.validatePath(media_path + '/tvshow.nfo')
            if xbmcvfs.exists(tvshow_nfo):
                nfo_path = tvshow_nfo

        if nfo_path is None:
            return

        with xbmcvfs.File(nfo_path) as file:
            nfo_contents = file.read()

        if nfo_contents == '':
            raise _ExportFailure(f'Unable to read NFO or file empty - "{nfo_path}"')

        try:
            self._xml = ElementTree.fromstring(nfo_contents)
        except ElementTree.ParseError as error:
            raise _ExportFailure(f'Unable to parse NFO file "{nfo_path}" due to error: {error}')

    @staticmethod
    def _replace_extension(path: str, extension: str) -> str:
        return os.path.splitext(path)[0] + extension

    @staticmethod
    def _replace_tail(path: str, new_tail: str) -> str:
        return os.path.split(path)[0] + new_tail

    @staticmethod
    def _decode_image(path: str) -> str:
        decoded_path = path.replace('image://', '', 1)
        decoded_path = urllib.parse.unquote(decoded_path)
        return decoded_path


def export(media_id: int, media_type: str):
    try:
        _Exporter(media_id, media_type).export()
    except _ExportFailure as failure:
        ADDON.log(failure)
