import datetime
import xml.etree.ElementTree as ElementTree
from typing import Callable, Optional, Union

import xbmcgui
import xbmcvfs

import resources.lib.media as media
import resources.lib.settings as settings
from resources.lib.addon import addon
from resources.lib.last_known import last_known

from . import *


class _DialogCancelled(Exception):
    pass


class _ExportFailure(Exception):
    pass


class ExportOne(Action):

    _type = 'Export One'

    # Ignoring label. It always gets returned and is a duplicate to title
    # so far as I can see. However, not sure if it is always the same as
    # title and isn't directly exportable, so rather than mapping label
    # to title and not requesting title, we're ignoring it.
    _ignored_fields = ['label', 'movieid', 'episodeid', 'tvshowid']
    _minimal_fields = ['playcount', 'lastplayed']

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
            info: media.MediaInfo,
            overwrite: Optional[bool] = None,
            subtask: bool = False
    ):
        super().__init__()

        self._is_subtask = subtask
        self._info = info

        self._is_minimal = False  # Placeholder
        # self._is_minimal = settings.export.is_minimal

        self._can_overwrite = overwrite
        if self._can_overwrite is None:
            self._can_overwrite = True  # Placeholder
            # self._can_overwrite = settings.export.can_overwrite

        self._tree = None
        self._read_nfo()
        if self._tree is None and settings.export.can_create_nfo:
            self._tree = ElementTree.Element(self._root_tags[self._info.type])

        self._cleared_arts = []
        self._fanart_tag = None

    def run(self) -> None:
        try:
            self._export()

        except _ExportFailure as failure:
            addon.log(f'Export Failure: {failure}')
            if not self._is_subtask:
                addon.notify(32043)

    def _export(self) -> None:
        if self._tree is None:
            return

        handlers = {
            'art': self._convert_art,
            'cast': self._convert_cast,
            'lastplayed': self._convert_lastplayed,
            'playcount': self._convert_playcount,
            'ratings': self._convert_ratings,
            'setid': self._convert_set,
            'streamdetails': self._convert_streamdetails,
            'uniqueid': self._convert_uniqueid,
            'trailer': self._convert_trailer
        }
        addon.log(f'Export - Source Info (Details):\n{self._info.details}', verbose=True)
        if self._is_minimal:
            for field in self._minimal_fields:
                if field not in self._info.details:
                    continue
                handler: Callable[..., None] = handlers.get(field, self._convert_generic)
                handler(field, self._info.details[field])
        else:
            for field, value in self._info.details.items():
                if field in self._ignored_fields:
                    continue
                handler: Callable[..., None] = handlers.get(field, self._convert_generic)
                handler(field, value)

            addon.log(f'Export - Source Info (Art):\n{self._info.art}', verbose=True)
            for art in self._info.art:
                self._convert_art(art)

            if self._info.type == 'tvshow':
                for season in self._info.seasons.values():
                    self._convert_season(season)

        self._write_nfo()

        timestamp = self._info.nfo_modification_time()
        if timestamp is None:
            addon.log(
                f'Unable to update timestamp for {self._info.type} with ID {self._info.id}'
                f'- could not get modified timestamp for file "{self._info.nfo}"'
            )
        else:
            last_known.set_timestamp(self._info.type, self._info.id, timestamp)

        last_known.set_checksum(self._info.type, self._info.id, self._info.checksum)

        if not self._is_subtask:
            last_known.write_changes()

    def _read_nfo(self) -> None:
        if self._info.nfo is None:
            return

        with xbmcvfs.File(self._info.nfo) as file:
            nfo_contents = file.read()

        if nfo_contents == '':
            raise _ExportFailure(f'Unable to read NFO or file empty - "{self._info.nfo}"')

        try:
            self._tree = ElementTree.fromstring(nfo_contents)
        except ElementTree.ParseError as error:
            raise _ExportFailure(f'Unable to parse NFO file "{self._info.nfo}" due to error: {error}')

    def _write_nfo(self):
        comment = ElementTree.Comment(
            f'Created {datetime.datetime.now().isoformat(" ", "seconds")} by {addon.name} {addon.version}'
        )
        self._tree.insert(0, comment)

        self._pretty_print(self._tree)

        if self._info.nfo is None:
            self._info.create_nfo_path()

        xml = ElementTree.tostring(self._tree, encoding='UTF-8', xml_declaration=True)
        with xbmcvfs.File(self._info.nfo, 'w') as file:
            success = file.write(xml)
        if not success:
            raise _ExportFailure(f'Unable to write NFO file "{self._info.nfo}"')

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
        if value == '':
            return

        if field in self._tag_remaps:
            tag = self._tag_remaps[field]
        else:
            tag = field

        if not self._try_clear_tags(tag):
            return

        if isinstance(value, list):
            for item in value:
                self._add_tag(self._tree, tag, str(item))
        else:
            self._add_tag(self._tree, tag, str(value))

    def _convert_art(self, art: dict, season: Optional[int] = None) -> None:
        type_ = art['arttype']
        preview = None
        if 'previewurl' in art:
            preview = media.decode_image(art['previewurl'])
        path = media.decode_image(art['url'])

        if self._is_ignored_image(type_, path, season):
            return

        if season is None and type_ == 'fanart':
            self._convert_fanart(preview, path)
        else:
            self._convert_thumb(type_, preview, path, season)

    def _is_ignored_image(self, type_: str, path: str, season: Optional[int] = None) -> bool:
        if (path == 'DefaultVideo.png'
                or path == 'DefaultFolder.png'
                or path.startswith('video@')
                or type_.startswith('tvshow.')
                or type_.startswith('season.')):
            return True

        extensionless_path = media.replace_extension(path, '')
        if self._info.type == 'tvshow':
            if extensionless_path == f'{self._info.file}{type_}':
                return True
            if season:
                season_name = 'season-specials' if season == 0 else f'season{season:02}'
                if (extensionless_path == f'{self._info.file}{season_name}-{type_}'
                        or extensionless_path == f'{self._info.file}season-all-{type_}'):
                    return True
        elif extensionless_path == f'{media.replace_extension(self._info.file, "")}-{type_}':
            return True

        return False

    def _convert_fanart(self, preview: Optional[str], path: str) -> None:
        # We only clean out fanart tags if we have fanart tags to set and we
        # only want to do this once so we don't clear out other new fanart tags
        if self._fanart_tag is None:
            if not self._try_clear_tags('fanart'):
                return
            self._fanart_tag = self._add_tag(self._tree, 'fanart')

        thumb = self._add_tag(self._fanart_tag, 'thumb', path)
        if preview:
            thumb.set('preview', str(preview))

    def _convert_thumb(self, type_: str, preview: Optional[str], path: str, season: Optional[int] = None) -> None:
        # We only clear out art tags of the same type and we only want to do
        # this once per art type, so as not delete new tags we're adding
        # Also, we want to do this seasonally for TV shows
        art_code = type_ if season is None else f'{type_}.season{season}'
        if art_code not in self._cleared_arts:
            if not self._try_clear_art(type_, season):
                return
            self._cleared_arts.append(art_code)

        element = self._add_tag(self._tree, 'thumb')
        element.text = path
        element.set('aspect', str(type_))
        if preview:
            element.set('preview', str(preview))
        if season is not None:
            element.set('season', str(season))
            element.set('type', 'season')

    def _try_clear_art(self, type_: str, season: Optional[int]) -> bool:
        if season is None:
            for elem in self._tree.findall(f'thumb[@aspect=\'{type_}\']'):
                # ElementTree doesn't let us filter by an attribute not existing,
                # so we just skip over season images in non-season image clears
                if elem.get('season'):
                    continue
                elif not self._can_overwrite:
                    return False
                self._tree.remove(elem)
        else:
            if not self._try_clear_tags(f'thumb[@aspect=\'{type_}\'][@season=\'{season}\']'):
                return False
        return True

    def _convert_cast(self, field: str, actors: list) -> None:
        del field

        existing_actors = self._tree.findall('actor')
        if existing_actors and (settings.export.actor_handling == settings.ActorOption.LEAVE
                                or not self._can_overwrite):
            return

        actor_bin = ElementTree.Element('bucket')

        if settings.export.actor_handling != settings.ActorOption.OVERWRITE:
            actor_bin.extend(existing_actors)

        for actor in existing_actors:
            self._tree.remove(actor)

        if settings.export.actor_handling == settings.ActorOption.UPDATE:
            self._update_cast(actors, actor_bin)
        else:
            self._merge_cast(actors, actor_bin)

    def _update_cast(self, new_actors: list, old_actors: ElementTree.Element):
        for element in old_actors:
            self._tree.append(element)
            actor_name = element.find('name').text
            details = next((a for a in new_actors if a['name'] == actor_name), None)
            if details is not None:
                self._update_actor(element, details)

    def _merge_cast(self, new_actors: list, old_actors: ElementTree.Element):
        for actor in new_actors:
            element = old_actors.find(f'*/[name=\'{actor["name"]}\']')
            if element is None:
                element = self._add_tag(self._tree, 'actor')
            else:
                self._tree.append(element)
            self._update_actor(element, actor)

    def _update_actor(self, element: ElementTree.Element, details: dict) -> None:
        if 'name' in details:
            self._set_tag(element, 'name', str(details['name']))
        if 'role' in details:
            self._set_tag(element, 'role', str(details['role']))
        if 'order' in details:
            self._set_tag(element, 'order', str(details['order']))
        if 'thumbnail' in details:
            self._set_tag(element, 'thumb', media.decode_image(details['thumbnail']))

    def _convert_lastplayed(self, field: str, date: str) -> None:
        del field
        self._set_tag(self._tree, 'lastplayed', date)

    def _convert_playcount(self, field: str, count: int) -> None:
        del field

        watched = 'true' if count > 0 else 'false'

        self._set_tag(self._tree, 'playcount', str(count))
        self._set_tag(self._tree, 'watched', watched)

    def _convert_ratings(self, field: str, ratings: dict) -> None:
        del field

        if not self._try_clear_tags('ratings'):
            return

        element = self._add_tag(self._tree, 'ratings')

        for rater, details in ratings.items():
            rating = self._add_tag(element, 'rating')

            rating.set('name', rater)
            rating.set('max', str(10))  # Regardless of origin, Kodi normalizes ratings to out-of-10
            if details.get('default'):
                rating.set('default', 'true')
            else:
                rating.set('default', 'false')

            self._add_tag(rating, 'value', str(round(details.get('rating', 0.0), 1)))
            if 'votes' in details:
                self._add_tag(rating, 'votes', str(details['votes']))

    def _convert_set(self, field: str, set_id: int) -> None:
        del field

        if set_id == 0:
            return

        if not self._try_clear_tags('set'):
            return

        element = self._add_tag(self._tree, 'set')
        self._add_tag(element, 'title', str(self._info.movieset['title']))
        self._add_tag(element, 'overview', str(self._info.movieset['plot']))

    def _convert_streamdetails(self, field: str, details: dict) -> None:
        del field

        if not self._try_clear_tags('fileinfo'):
            return

        file_info = self._add_tag(self._tree, 'fileinfo')
        stream_details = self._add_tag(file_info, 'streamdetails')

        for video_info in details['video']:
            video_info['aspect'] = f'{video_info.get("aspect", 0):.6f}'
            video_info['durationinseconds'] = video_info.pop('duration', None)
            self._add_details_set('video', stream_details, video_info)
        for audio_info in details['audio']:
            self._add_details_set('audio', stream_details, audio_info)
        for subtitle_info in details['subtitle']:
            self._add_details_set('subtitle', stream_details, subtitle_info)

    def _add_details_set(self, details_type: str, parent: ElementTree.Element, info_set: dict) -> None:
        element = self._add_tag(parent, details_type)
        for proprty, value in info_set.items():
            if value is None or value == '':
                continue
            self._add_tag(element, proprty, str(value))

    def _convert_trailer(self, field: str, path: str) -> None:
        del field

        if media.replace_extension(path, '') == f'{media.replace_extension(self._info.file, "")}-trailer':
            return
        if path.startswith('plugin://') and not settings.export.should_export_plugin_trailers:
            return

        if not self._try_clear_tags('trailer'):
            return

        self._add_tag(self._tree, 'trailer', str(path))

    def _convert_uniqueid(self, field: str, unique_ids: dict) -> None:
        del field

        default = None
        default_tag = self._tree.find(f'uniqueid[@default=\'true\']')
        if default_tag:
            default = default_tag.get('type', None)

        if not self._try_clear_tags('uniqueid'):
            return

        for service, service_id in unique_ids.items():
            element = self._add_tag(self._tree, 'uniqueid', str(service_id))
            element.set('type', str(service))
            if service == default:
                element.set('default', 'true')

    def _convert_season(self, season: media.SeasonInfo) -> None:
        addon.log(f'Export - Source JSON (Season {season.details["season"]} Details):\n{season.details}', verbose=True)
        if 'title' in season.details and self._try_clear_tags(f'namedseason[@number=\'{season.details["season"]}\']'):
            named_season = self._add_tag(self._tree, 'namedseason', str(season.details['title']))
            named_season.set('number', str(season.details['season']))

        addon.log(f'Export - Source JSON (Season {season.details["season"]} Art):\n{season.art}', verbose=True)
        for art in season.art:
            self._convert_art(art, season.details['season'])

    def _add_tag(self, parent: ElementTree.Element, tag: str, text: Optional[str] = None) -> ElementTree.Element:
        element = ElementTree.SubElement(parent, tag)
        if text is not None:
            element.text = text
        return element

    def _set_tag(self, parent: ElementTree.Element, tag: str, text: Optional[str] = None) -> ElementTree.Element:
        for element in parent.findall(tag):
            parent.remove(element)
        element = self._add_tag(parent, tag, text)
        return element

    def _try_clear_tags(self, search: str) -> bool:
        elements = self._tree.findall(search)
        if elements and not self._can_overwrite:
            return False
        for element in elements:
            self._tree.remove(element)
        return True


class ExportAll(Action):

    _type = 'Export All'

    def run(self) -> None:
        dialog = xbmcgui.DialogProgress()
        dialog.create(addon.getLocalizedString(32069))

        failures = False

        def export_type(type_: str, message: int, fraction: int, base_progress: int) -> bool:
            type_info = media.TYPE_INFO[type_]

            full_success = True
            items = media.get_all(type_)
            count = 0
            total = len(items)
            for item in items:
                ExportOne(media.MediaInfo(type_, item[type_info.id_name], file=item['file']), subtask=True).run()
                success = True  # Let's just assume for now, until the error handling pass
                if not success:
                    full_success = False
                if dialog.iscanceled():
                    raise _DialogCancelled
                count += 1
                progress = int(count / total * fraction) + base_progress
                dialog.update(progress, addon.getLocalizedString(message))

            return full_success

        try:
            if not export_type(type_='movie', message=32070, fraction=33, base_progress=0):
                failures = True
            if not export_type(type_='tvshow', message=32071, fraction=33, base_progress=33):
                failures = True
            if not export_type(type_='episode', message=32072, fraction=34, base_progress=66):
                failures = True

        except _DialogCancelled:
            pass

        finally:
            last_known.write_changes()
            dialog.close()
            if failures:
                addon.notify(32073)
