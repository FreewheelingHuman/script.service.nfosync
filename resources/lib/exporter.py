import datetime
import xml.etree.ElementTree as ElementTree
from typing import Callable, Final, Optional

import xbmcvfs

import resources.lib.filetools as filetools
import resources.lib.media as media
from resources.lib.addon import ADDON
from resources.lib.settings import SYNC, STATE, ActorTagOption, TrailerTagOption, MovieNfoType


class _ExportFailure(Exception):
    pass


class _Exporter:
    # Ignoring label. It always gets returned and is a duplicate to title
    # so far as I can see. However, not sure if it is always the same as
    # title and isn't directly exportable, so rather than mapping label
    # to title and not requesting title, we're ignoring it.
    _ignored_fields = ['label', 'movieid', 'episodeid', 'tvshowid']

    _root_tags = {
        'movie': 'movie',
        'tvshow': 'tvshow',
        'episode': 'episodedetails'
    }

    _tag_remaps = {
        'plotoutline': 'outline',
        'writer': 'credits',
        'firstaired': 'aired',
        'specialsortseason': 'displayseason',
        'specialsortepisode': 'displayepisode'
    }

    def __init__(
            self,
            media_type: str,
            library_id: int,
            bulk: bool,
            media_path: Optional[str] = None,
            nfo_path: Optional[str] = None,
            media_info: media.MediaInfo = None
    ):
        self._bulk = bulk
        self._library_id = library_id
        self._media_type = media_type
        self._media_info = media_info

        self._media_path = media_path
        if self._media_path is None:
            self._media_path = media.get_file(self._media_type, self._library_id)

        self._xml = None
        self._nfo_path = nfo_path
        self._read_nfo()
        if self._xml is None and SYNC.create_nfo:
            self._xml = ElementTree.Element(self._root_tags[self._media_type])

        self._cleared_arts = []
        self._fanart_tag = None

    def export(self) -> None:
        if self._xml is None:
            return

        if self._media_info is None:
            self._media_info = media.get_info(self._media_type, self._library_id)

        handlers = {
            'art': self._convert_art,
            'cast': self._convert_cast,
            'playcount': self._convert_playcount,
            'ratings': self._convert_ratings,
            'setid': self._convert_set,
            'streamdetails': self._convert_streamdetails,
            'uniqueid': self._convert_uniqueid,
            'trailer': self._convert_trailer
        }
        ADDON.log(f'Export - Source Info (Details):\n{self._media_info.details}', verbose=True)
        for field, value in self._media_info.details.items():
            if field in self._ignored_fields:
                continue
            handler: Callable[..., None] = handlers.get(field, self._convert_generic)
            handler(field, value)

        ADDON.log(f'Export - Source Info (Art):\n{self._media_info.art}', verbose=True)
        for art in self._media_info.art:
            self._convert_art(art)

        if self._media_type == 'tvshow':
            for season in self._media_info.seasons.values():
                self._convert_season(season)

        self._write_nfo()

        timestamp = filetools.get_modification_time(self._nfo_path)
        STATE.set_timestamp(self._media_type, self._library_id, timestamp)
        if not self._bulk:
            STATE.write_changes()

    def _read_nfo(self) -> None:
        if self._media_type == 'movie':
            self._nfo_path = filetools.get_movie_nfo(self._media_path)
        elif self._media_type == 'episode':
            self._nfo_path = filetools.get_episode_nfo(self._media_path)
        elif self._media_type == 'tvshow':
            self._nfo_path = filetools.get_tvshow_nfo(self._media_path)

        if self._nfo_path is None:
            return

        with xbmcvfs.File(self._nfo_path) as file:
            nfo_contents = file.read()

        if nfo_contents == '':
            raise _ExportFailure(f'Unable to read NFO or file empty - "{self._nfo_path}"')

        try:
            self._xml = ElementTree.fromstring(nfo_contents)
        except ElementTree.ParseError as error:
            raise _ExportFailure(f'Unable to parse NFO file "{self._nfo_path}" due to error: {error}')

    def _write_nfo(self):
        comment = ElementTree.Comment(
            f'Created {datetime.datetime.now().isoformat(" ", "seconds")} by {ADDON.name} {ADDON.version}'
        )
        self._xml.insert(0, comment)

        self._pretty_print(self._xml)

        if self._nfo_path is None:
            self._generate_nfo_path()

        with xbmcvfs.File(self._nfo_path, 'w') as file:
            success = file.write(ElementTree.tostring(self._xml, encoding="UTF-8", xml_declaration=True))
        if not success:
            raise _ExportFailure(f'Unable to write NFO file "{self._nfo_path}"')

    def _generate_nfo_path(self) -> None:
        if self._media_type == 'movie':
            if SYNC.movie_nfo == MovieNfoType.MOVIE:
                self._nfo_path = filetools.create_movie_movie_nfo(self._media_path)
            else:
                self._nfo_path = filetools.create_movie_filename_nfo(self._media_path)
        elif self._media_type == 'episode':
            self._nfo_path = filetools.create_episode_nfo(self._media_path)
        elif self._media_type == 'tvshow':
            self._nfo_path = filetools.create_tvshow_nfo(self._media_path)

    def _pretty_print(self, element, level=1) -> None:
        def indent(indent_level):
            return '\n' + '    ' * indent_level

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

    def _convert_art(self, art: dict, season: Optional[int] = None) -> None:
        art_type = art['arttype']
        preview = None
        if 'previewurl' in art:
            preview = filetools.decode_image(art['previewurl'])
        path = filetools.decode_image(art['url'])

        if self._is_ignored_image(art_type, path, season):
            return

        if season is None and art_type == 'fanart':
            self._set_fanart(preview, path)
        else:
            self._set_thumb(art_type, preview, path, season)

    def _is_ignored_image(self, aspect: str, path: str, season: Optional[int] = None) -> bool:
        if (path == 'DefaultVideo.png'
                or path == 'DefaultFolder.png'
                or path.startswith('video@')
                or aspect.startswith('tvshow.')
                or aspect.startswith('season.')):
            return True

        extensionless_path = filetools.replace_extension(path, '')
        if self._media_type == 'tvshow':
            if extensionless_path == f'{self._media_path}{aspect}':
                return True
            if season:
                season_name = 'season-specials' if season == 0 else f'season{season:02}'
                if (extensionless_path == f'{self._media_path}{season_name}-{aspect}'
                        or extensionless_path == f'{self._media_path}season-all-{aspect}'):
                    return True
        elif extensionless_path == f'{filetools.replace_extension(self._media_path, "")}-{aspect}':
            return True

        return False

    def _set_fanart(self, preview: Optional[str], path: str) -> None:
        # We only clean out fanart tags if we have fanart tags to set and we
        # only want to do this once so we don't clear out other new fanart tags
        if self._fanart_tag is None:
            self._fanart = self._set_tag(self._xml, 'fanart', None)

        thumb = self._add_tag(self._fanart, 'thumb', path)
        if preview:
            thumb.set('preview', str(preview))

    def _set_thumb(self, art_type: str, preview: Optional[str], path: str, season: Optional[int] = None) -> None:
        # We only clear out art tags of the same type and we only want to do
        # this once per art type, so as not delete new tags we're adding
        # Also, we want to do this seasonally for TV shows
        art_code = art_type if season is None else f'{art_type}.season{season}'
        if art_code not in self._cleared_arts:
            self._cleared_arts.append(art_code)
            self._clear_art(art_type, season)

        element = self._add_tag(self._xml, 'thumb')
        element.text = path
        element.set('aspect', str(art_type))
        if preview:
            element.set('preview', str(preview))
        if season is not None:
            element.set('season', str(season))
            element.set('type', 'season')

    def _clear_art(self, art_type: str, season: Optional[int]) -> None:
        if season is None:
            for elem in self._xml.findall(f'thumb[@aspect=\'{art_type}\']'):
                # ElementTree doesn't let us filter by an attribute not existing,
                # so we just skip over season images in non-season image clears
                if elem.get('season'):
                    continue
                self._xml.remove(elem)
        else:
            for elem in self._xml.findall(f'thumb[@aspect=\'{art_type}\'][@season=\'{season}\']'):
                self._xml.remove(elem)

    def _convert_cast(self, field: str, actors: list) -> None:
        del field

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

    def _convert_playcount(self, field: str, count) -> None:
        del field

        watched = 'true' if count > 0 else 'false'

        self._set_tag(self._xml, 'playcount', count)
        self._set_tag(self._xml, 'watched', watched)

    def _convert_ratings(self, field: str, ratings: dict) -> None:
        del field

        ratings_elem = self._set_tag(self._xml, 'ratings', None)

        for rater, details in ratings.items():
            rating = self._add_tag(ratings_elem, 'rating')

            rating.set('name', rater)
            rating.set('max', str(10))  # Regardless of origin, Kodi normalizes ratings to out-of-10
            if details.get('default'):
                rating.set('default', 'true')
            else:
                rating.set('default', 'false')

            self._add_tag(rating, 'value', round(details.get('rating', 0.0), 1))
            if 'votes' in details:
                self._add_tag(rating, 'votes', details['votes'])

    def _convert_set(self, field: str, set_id: int) -> None:
        del field

        self._remove_tags(self._xml, 'set')

        if set_id == 0:
            return

        details, _ = mediatools.get_details('movieset', set_id)

        st = self._add_tag(self._xml, 'set')
        self._add_tag(st, 'title', details['title'])
        self._add_tag(st, 'overview', details['plot'])

    def _convert_streamdetails(self, field: str, details: dict) -> None:
        del field

        self._remove_tags(self._xml, 'fileinfo')
        fileinfo = self._add_tag(self._xml, 'fileinfo')
        streamdetails = self._add_tag(fileinfo, 'streamdetails')

        for video_info in details['video']:
            video_info['aspect'] = f'{video_info.get("aspect", 0):.6f}'
            video_info['durationinseconds'] = video_info.pop('duration', None)
            self._process_details_set('video', streamdetails, video_info)
        for audio_info in details['audio']:
            self._process_details_set('audio', streamdetails, audio_info)
        for subtitle_info in details['subtitle']:
            self._process_details_set('subtitle', streamdetails, subtitle_info)

    def _process_details_set(self, details_type: str, parent: ElementTree.Element, info_set: dict) -> None:
        element = self._add_tag(parent, details_type)
        for proprty, value in info_set.items():
            if value is None or value == '':
                continue
            self._add_tag(element, proprty, value)

    def _convert_trailer(self, field: str, path: str) -> None:
        del field

        if SYNC.trailer == TrailerTagOption.SKIP:
            return
        if filetools.replace_extension(path, '') == f'{filetools.replace_extension(self._media_path, "")}-trailer':
            return
        if SYNC.trailer == TrailerTagOption.NO_PLUGIN and path.startswith('plugin://'):
            return

        self._set_tag(self._xml, 'trailer', path)

    def _convert_uniqueid(self, field: str, unique_ids: dict) -> None:
        del field

        default = None
        default_tag = self._xml.find(f'uniqueid[@default=\'true\']')
        if default_tag:
            default = default_tag.get('type', None)

        self._remove_tags(self._xml, 'uniqueid')

        for service, service_id in unique_ids.items():
            element = self._add_tag(self._xml, 'uniqueid', service_id)
            element.set('type', service)
            if service == default:
                element.set('default', 'true')

    def _convert_season(self, season: media.SeasonInfo) -> None:
        ADDON.log(f'Export - Source JSON (Season {season.details["season"]} Details):\n{season.details}', verbose=True)
        if 'title' in season.details:
            for tag in self._xml.findall(f'namedseason[@number=\'{season.details["season"]}\']'):
                self._xml.remove(tag)
            named_season = self._add_tag(self._xml, 'namedseason', season.details['title'])
            named_season.set('number', str(season.details['season']))

        ADDON.log(f'Export - Source JSON (Season {season.details["season"]} Art):\n{season.art}', verbose=True)
        for art in season.art:
            self._convert_art(art, season.details['season'])

    def _add_tag(self, parent: ElementTree.Element, tag: str, text: Optional[str] = None) -> ElementTree.Element:
        element = ElementTree.SubElement(parent, tag)
        if text is not None:
            element.text = str(text)
        return element

    def _set_tag(self, parent: ElementTree.Element, tag: str, text: Optional[str]) -> ElementTree.Element:
        self._remove_tags(parent, tag)
        element = self._add_tag(parent, tag, text)
        return element

    def _remove_tags(self, parent: ElementTree.Element, tag: str) -> None:
        for element in parent.findall(tag):
            parent.remove(element)


def export(
        media_type: str,
        library_id: int,
        media_path: Optional[str] = None,
        nfo_path: Optional[str] = None,
        media_info: Optional[media.MediaInfo] = None,
        bulk: bool = False
) -> bool:
    try:
        exporter = _Exporter(
            media_type=media_type,
            library_id=library_id,
            bulk=bulk,
            media_path=media_path,
            nfo_path=nfo_path,
            media_info=media_info
        )
        exporter.export()

    except _ExportFailure as failure:
        ADDON.log(str(failure))
        if not bulk:
            ADDON.notify(ADDON.getLocalizedString(32043))
        return False

    return True
