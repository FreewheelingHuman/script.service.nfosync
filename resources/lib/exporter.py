import datetime
import xml.etree.ElementTree as ElementTree
from typing import Callable, Optional, Union

import xbmcvfs

import resources.lib.filetools as filetools
import resources.lib.media as media
import resources.lib.settings as settings
from resources.lib.addon import addon
from resources.lib.last_known import last_known


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
            type_: str,
            id_: int,
            subtask: bool,
            file: Optional[str] = None,
            nfo: Optional[str] = None,
            info: media.MediaInfo = None
    ):
        self._is_subtask = subtask
        self._id = id_
        self._type = type_
        self._info = info

        self._file = file
        if self._file is None:
            self._file = media.file(self._type, self._id)

        self._xml = None
        self._nfo = nfo
        self._read_nfo()
        if self._xml is None and settings.export.can_create_nfo:
            self._xml = ElementTree.Element(self._root_tags[self._type])

        self._cleared_arts = []
        self._fanart_tag = None

    def export(self) -> None:
        if self._xml is None:
            return

        if self._info is None:
            self._info = media.info(self._type, self._id)

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
        addon.log(f'Export - Source Info (Details):\n{self._info.details}', verbose=True)
        for field, value in self._info.details.items():
            if field in self._ignored_fields:
                continue
            handler: Callable[..., None] = handlers.get(field, self._convert_generic)
            handler(field, value)

        addon.log(f'Export - Source Info (Art):\n{self._info.art}', verbose=True)
        for art in self._info.art:
            self._convert_art(art)

        if self._type == 'tvshow':
            for season in self._info.seasons.values():
                self._convert_season(season)

        self._write_nfo()

        timestamp = filetools.modification_time(self._nfo)
        if timestamp is None:
            addon.log(
                f'Unable to update timestamp for {self._type} with ID {self._id}'
                f'- could not get modified timestamp for file "{self._nfo}"'
            )
        else:
            last_known.set_timestamp(self._type, self._id, timestamp)

        last_known.set_checksum(self._type, self._id, self._info.checksum)

        if not self._is_subtask:
            last_known.write_changes()

    def _read_nfo(self) -> None:
        if self._type == 'movie':
            self._nfo = filetools.find_movie_nfo(self._file)
        elif self._type == 'episode':
            self._nfo = filetools.find_episode_nfo(self._file)
        elif self._type == 'tvshow':
            self._nfo = filetools.find_tvshow_nfo(self._file)

        if self._nfo is None:
            return

        with xbmcvfs.File(self._nfo) as file:
            nfo_contents = file.read()

        if nfo_contents == '':
            raise _ExportFailure(f'Unable to read NFO or file empty - "{self._nfo}"')

        try:
            self._xml = ElementTree.fromstring(nfo_contents)
        except ElementTree.ParseError as error:
            raise _ExportFailure(f'Unable to parse NFO file "{self._nfo}" due to error: {error}')

    def _write_nfo(self):
        comment = ElementTree.Comment(
            f'Created {datetime.datetime.now().isoformat(" ", "seconds")} by {addon.name} {addon.version}'
        )
        self._xml.insert(0, comment)

        self._pretty_print(self._xml)

        if self._nfo is None:
            self._generate_nfo_path()

        with xbmcvfs.File(self._nfo, 'w') as file:
            success = file.write(ElementTree.tostring(self._xml, encoding='UTF-8', xml_declaration=True))
        if not success:
            raise _ExportFailure(f'Unable to write NFO file "{self._nfo}"')

    def _generate_nfo_path(self) -> None:
        if self._type == 'movie':
            if settings.export.movie_nfo_naming == settings.MovieNfoOption.MOVIE:
                self._nfo = filetools.movie_movie_nfo(self._file)
            else:
                self._nfo = filetools.movie_filename_nfo(self._file)
        elif self._type == 'episode':
            self._nfo = filetools.episode_nfo(self._file)
        elif self._type == 'tvshow':
            self._nfo = filetools.tvshow_nfo(self._file)

    def _pretty_print(self, element: ElementTree.Element, level=1) -> None:
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

    def _convert_generic(self, field: str, value: Union[str, list]) -> None:
        if field in self._tag_remaps:
            tag = self._tag_remaps[field]
        else:
            tag = field

        self._remove_tags(self._xml, tag)

        if value == '':
            return

        if isinstance(value, list):
            for item in value:
                self._add_tag(self._xml, tag, item)
        else:
            self._add_tag(self._xml, tag, value)

    def _convert_art(self, art: dict, season: Optional[int] = None) -> None:
        type_ = art['arttype']
        preview = None
        if 'previewurl' in art:
            preview = filetools.decode_image(art['previewurl'])
        path = filetools.decode_image(art['url'])

        if self._is_ignored_image(type_, path, season):
            return

        if season is None and type_ == 'fanart':
            self._set_fanart(preview, path)
        else:
            self._set_thumb(type_, preview, path, season)

    def _is_ignored_image(self, type_: str, path: str, season: Optional[int] = None) -> bool:
        if (path == 'DefaultVideo.png'
                or path == 'DefaultFolder.png'
                or path.startswith('video@')
                or type_.startswith('tvshow.')
                or type_.startswith('season.')):
            return True

        extensionless_path = filetools.replace_extension(path, '')
        if self._type == 'tvshow':
            if extensionless_path == f'{self._file}{type_}':
                return True
            if season:
                season_name = 'season-specials' if season == 0 else f'season{season:02}'
                if (extensionless_path == f'{self._file}{season_name}-{type_}'
                        or extensionless_path == f'{self._file}season-all-{type_}'):
                    return True
        elif extensionless_path == f'{filetools.replace_extension(self._file, "")}-{type_}':
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

    def _set_thumb(self, type_: str, preview: Optional[str], path: str, season: Optional[int] = None) -> None:
        # We only clear out art tags of the same type and we only want to do
        # this once per art type, so as not delete new tags we're adding
        # Also, we want to do this seasonally for TV shows
        art_code = type_ if season is None else f'{type_}.season{season}'
        if art_code not in self._cleared_arts:
            self._cleared_arts.append(art_code)
            self._clear_art(type_, season)

        element = self._add_tag(self._xml, 'thumb')
        element.text = path
        element.set('aspect', str(type_))
        if preview:
            element.set('preview', str(preview))
        if season is not None:
            element.set('season', str(season))
            element.set('type', 'season')

    def _clear_art(self, type_: str, season: Optional[int]) -> None:
        if season is None:
            for elem in self._xml.findall(f'thumb[@aspect=\'{type_}\']'):
                # ElementTree doesn't let us filter by an attribute not existing,
                # so we just skip over season images in non-season image clears
                if elem.get('season'):
                    continue
                self._xml.remove(elem)
        else:
            for elem in self._xml.findall(f'thumb[@aspect=\'{type_}\'][@season=\'{season}\']'):
                self._xml.remove(elem)

    def _convert_cast(self, field: str, actors: list) -> None:
        del field

        actor_bin = ElementTree.Element('bucket')
        existing_actors = self._xml.findall('actor')

        if existing_actors and settings.export.actor_handling == settings.ActorOption.LEAVE:
            return

        if settings.export.actor_handling != settings.ActorOption.OVERWRITE:
            actor_bin.extend(existing_actors)

        for actor in existing_actors:
            self._xml.remove(actor)

        if settings.export.actor_handling == settings.ActorOption.UPDATE:
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

        element = self._set_tag(self._xml, 'ratings', None)

        for rater, details in ratings.items():
            rating = self._add_tag(element, 'rating')

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

        st = self._add_tag(self._xml, 'set')
        self._add_tag(st, 'title', self._info.movieset['title'])
        self._add_tag(st, 'overview', self._info.movieset['plot'])

    def _convert_streamdetails(self, field: str, details: dict) -> None:
        del field

        self._remove_tags(self._xml, 'fileinfo')
        file_info = self._add_tag(self._xml, 'fileinfo')
        stream_details = self._add_tag(file_info, 'streamdetails')

        for video_info in details['video']:
            video_info['aspect'] = f'{video_info.get("aspect", 0):.6f}'
            video_info['durationinseconds'] = video_info.pop('duration', None)
            self._process_details_set('video', stream_details, video_info)
        for audio_info in details['audio']:
            self._process_details_set('audio', stream_details, audio_info)
        for subtitle_info in details['subtitle']:
            self._process_details_set('subtitle', stream_details, subtitle_info)

    def _process_details_set(self, details_type: str, parent: ElementTree.Element, info_set: dict) -> None:
        element = self._add_tag(parent, details_type)
        for proprty, value in info_set.items():
            if value is None or value == '':
                continue
            self._add_tag(element, proprty, value)

    def _convert_trailer(self, field: str, path: str) -> None:
        del field

        if filetools.replace_extension(path, '') == f'{filetools.replace_extension(self._file, "")}-trailer':
            return
        if path.startswith('plugin://') and not settings.export.should_export_plugin_trailers:
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
        addon.log(f'Export - Source JSON (Season {season.details["season"]} Details):\n{season.details}', verbose=True)
        if 'title' in season.details:
            for tag in self._xml.findall(f'namedseason[@number=\'{season.details["season"]}\']'):
                self._xml.remove(tag)
            named_season = self._add_tag(self._xml, 'namedseason', season.details['title'])
            named_season.set('number', str(season.details['season']))

        addon.log(f'Export - Source JSON (Season {season.details["season"]} Art):\n{season.art}', verbose=True)
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
        type_: str,
        id_: int,
        file: Optional[str] = None,
        nfo: Optional[str] = None,
        info: Optional[media.MediaInfo] = None,
        subtask: bool = False
) -> bool:
    try:
        exporter = _Exporter(
            type_=type_,
            id_=id_,
            subtask=subtask,
            file=file,
            nfo=nfo,
            info=info
        )
        exporter.export()

    except _ExportFailure as failure:
        addon.log(f'Export Failure: {failure}')
        if not subtask:
            addon.notify(addon.getLocalizedString(32043))
        return False

    return True
