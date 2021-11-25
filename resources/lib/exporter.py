import collections
import xml.etree.ElementTree as ElementTree
import xbmc
from typing import Callable, Final, Optional

import xbmcvfs

import resources.lib.filetools as filetools
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
        'streamdetails', 'top250', 'sorttitle', 'dateadded', 'tag',
        'art', 'userrating', 'ratings', 'premiered', 'uniqueid'
    ]

    _episode_fields: Final = [
        'title', 'plot', 'writer', 'firstaired', 'playcount', 'runtime',
        'director', 'season', 'episode', 'originaltitle', 'showtitle', 'cast',
        'streamdetails', 'lastplayed', 'dateadded', 'uniqueid', 'art',
        'specialsortseason', 'specialsortepisode', 'userrating', 'ratings'
    ]

    _tvshow_fields: Final = [
        'title', 'genre', 'year', 'plot', 'studio', 'mpaa', 'cast', 'playcount',
        'episode', 'premiered', 'lastplayed', 'originaltitle',
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
            'ratings': self._convert_ratings,
            'setid': self._convert_set,
            'streamdetails': self._convert_streamdetails,
            'uniqueid': self._convert_uniqueid,
            'trailer': self._convert_trailer
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
        for field, value in details.items():
            if field in self._ignored_fields:
                continue
            handler: Callable[..., None] = self._handlers.get(field, self._convert_generic)
            handler(field, value)

        self._pretty_print(self._xml)
        xbmc.log(f'Behold! XML:\n{ElementTree.tostring(self._xml, encoding="unicode")}')

    def _import_nfo(self, media_path: str) -> None:
        if media_path is None or media_path == '':
            raise _ExportFailure(f'Empty media path for library id "{self._media_id}"')

        nfo_path = None

        if self._media_type == self._type_info['movie']:
            nfo_path = filetools.get_movie_nfo(media_path)
        elif self._media_type == self._type_info['episode']:
            nfo_path = filetools.get_episode_nfo(media_path)
        elif self._media_type == self._type_info['tvshow']:
            nfo_path = filetools.get_tvshow_nfo(media_path)

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

    def _pretty_print(self, element, level=1) -> None:
        def indent(ilevel):
            return '\n' + '    ' * ilevel

        if len(element):
            if element.text is None or element.text.strip() == '':
                element.text = indent(level)
            for subelement in range(len(element)-1):
                element[subelement].tail = indent(level)
                self._pretty_print(element[subelement], level+1)
            element[-1].tail = indent(level-1)
            self._pretty_print(element[-1], level+1)

    def _convert_generic(self, field: str, value) -> None:
        if field in self._tag_remaps:
            tag = self._tag_remaps[field]
        else:
            tag = field

        self._remove_tags(self._xml, tag)

        if value is None or value == '':
            return

        if isinstance(value, list):
            for item in value:
                self._add_tag(self._xml, tag, item)
        else:
            self._add_tag(self._xml, tag, value)

    def _convert_art(self, field: str, value, season: Optional[int] = None) -> None:
        for aspect, coded_path in value.items():
            path = filetools.decode_image(coded_path)

            if self._is_ignored_image(aspect, path, season):
                continue

            if season is None and aspect.startswith('fanart'):
                self._set_fanart(path)
            else:
                self._set_thumb(aspect, path, season)

    def _is_ignored_image(self, aspect: str, path: str, season: Optional[int] = None) -> bool:
        if (path == 'DefaultVideo.png'
                or path == 'DefaultFolder.png'
                or path.startswith('video@')
                or aspect.startswith('tvshow.')
                or aspect.startswith('season.')):
            return True

        extensionless_path = filetools.replace_extension(path, '')
        if self._media_type == self._type_info['tvshow']:
            if extensionless_path == f'{self._file}{aspect}':
                return True
            if season:
                season_name = 'season-specials' if season == 0 else f'season{season:02}'
                if (extensionless_path == f'{self._file}{season_name}-{aspect}'
                        or extensionless_path == f'{self._file}season-all-{aspect}'):
                    return True
        elif extensionless_path == f'{filetools.replace_extension(self._file, "")}-{aspect}':
            return True

        return False

    def _set_fanart(self, path: str) -> None:
        fanart = self._merge_tags(self._xml, 'fanart')
        if fanart is None:
            fanart = self._add_tag(self._xml, 'fanart')

        thumb = fanart.find(f'[thumb=\'{path}\']')
        if thumb is None:
            self._add_tag(fanart, 'thumb', path)

    def _set_thumb(self, aspect: str, path: str, season: Optional[int] = None) -> None:
        if season:
            query = f'thumb[@aspect=\'{aspect}\'][@season=\'{season}\']'
        else:
            query = f'thumb[@aspect=\'{aspect}\']'
        element = self._xml.find(query)
        if element is None:
            element = self._add_tag(self._xml, 'thumb')

        element.text = path
        element.set('aspect', aspect)
        if season:
            element.set('season', str(season))
            element.set('type', 'season')

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

    def _update_actor(self, element: ElementTree.Element, details: dict) -> None:
        if 'name' in details:
            self._set_tag(element, 'name', details['name'])
        if 'role' in details:
            self._set_tag(element, 'role', details['role'])
        if 'order' in details:
            self._set_tag(element, 'order', details['order'])
        if 'thumbnail' in details:
            self._set_tag(element, 'thumb', filetools.decode_image(details['thumbnail']))

    def _convert_ratings(self, field: str, value) -> None:
        self._remove_tags(self._xml, 'ratings')
        ratings = self._add_tag(self._xml, 'ratings')

        for rater, details in value.items():
            rating = self._add_tag(ratings, 'rating')

            rating.set('name', rater)
            rating.set('max', str(10))
            if details.get('default'):
                rating.set('default', 'true')
            else:
                rating.set('default', 'false')

            self._add_tag(rating, 'value', round(details.get('rating', 0.0), 1))
            self._add_tag(rating, 'votes', details.get('votes', 0))

    def _convert_set(self, field: str, value) -> None:
        xbmc.log(f'convert set: {field} with value {value}')

    def _convert_streamdetails(self, field: str, value) -> None:
        xbmc.log(f'convert streamdetails: {field} with value {value}')

    def _convert_trailer(self, field: str, value) -> None:
        xbmc.log(f'convert trailer: {field} with value {value}')

    def _convert_uniqueid(self, field: str, value) -> None:
        xbmc.log(f'convert uniqueid: {field} with value {value}')

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

    def _merge_tags(self, parent: ElementTree.Element, tag: str) -> Optional[ElementTree.Element]:
        elements = parent.findall(tag)
        if not elements:
            return None
        elif len(elements) == 1:
            return elements[0]
        adopter = elements[0]
        adoptees = parent.findall(f'{tag}/*')
        adopter.clear()
        adopter.extend(adoptees)
        for leftover in elements[1:]:
            parent.remove(leftover)
        return adopter

    def _remove_tags(self, parent: ElementTree.Element, tag: str) -> None:
        for element in parent.findall(tag):
            parent.remove(element)

def export(media_id: int, media_type: str):
    try:
        _Exporter(media_id, media_type).export()
    except _ExportFailure as failure:
        ADDON.log(failure)
