from typing import Iterator, Optional, Final

import resources.lib.gui as gui
import resources.lib.jsonrpc as jsonrpc
import resources.lib.media as media
from resources.lib.addon import addon

from . import *
from . import _PhasedAction


class ImportOne(Action):

    _type: Final = 'Import One'

    def __init__(self, info: media.MediaInfo):
        super().__init__()
        self._info = info
        self._awaiting_id = None

    def run(self, data: Optional[dict] = None) -> bool:
        if not self._awaiting:
            self._request()
        else:
            if not data:
                return False

            if self._info.type == 'tvshow' and data.get('item') and data['item'].get('id') == self._awaiting_id:
                self._awaiting = None
                self._awaiting_id = None
                return False
            elif data.get('id') == self._awaiting_id:
                self._awaiting = None
                self._awaiting_id = None
                return True

            return False

    def _request(self) -> None:
        parameters = {media.TYPE_INFO[self._info.type].id_name: self._info.id}
        if self._info.type == 'tvshow':
            parameters['refreshepisodes'] = True

        try:
            jsonrpc.request(
                media.TYPE_INFO[self._info.type].refresh_method,
                **parameters
            )
            addon.log(f'Import - A refresh has been requested for "{self._info.file}"', verbose=True)
        except jsonrpc.RequestError as error:
            raise ActionError(32007, f'Import - Unable to request refresh for "{self._info.file}"') from error

        self._awaiting_id = self._info.id
        if self._info.type == 'tvshow':
            self._awaiting = 'VideoLibrary.OnUpdate'
        else:
            self._awaiting = 'VideoLibrary.OnRemove'


_import_all_progress = gui.AllActionProgress(32065)


class _ImportType(_PhasedAction):

    _type: Final = 'Import Type'

    def __init__(self, type_: str, message: int):
        super().__init__()
        self._media_type = type_
        self._message = message

    def _phases(self) -> Iterator[Action]:
        type_info = media.TYPE_INFO[self._media_type]
        items = media.get_all(self._media_type)
        count = 0
        total = len(items)
        for item in items:
            if _import_all_progress.is_canceled:
                break
            _import_all_progress.set(self._message, count, total)
            yield ImportOne(media.MediaInfo(self._media_type, item[type_info.id_name], file=item['file']))
            count += 1


class ImportAll(_PhasedAction):

    _type: Final = 'Import All'

    _types_to_import = {
        'movie': 32066,
        'tvshow': 32067,
        'episode': 32068
    }

    def _phases(self) -> Iterator[Action]:
        for type_, message in self._types_to_import.items():
            if _import_all_progress.is_canceled:
                break
            yield _ImportType(type_=type_, message=message)

    def _exception(self, error: Exception) -> None:
        if isinstance(error, ActionError):
            raise ActionError(32085, f'Import - Unable to complete Import All"') from error
        super()._exception(error)

    def _cleanup(self):
        _import_all_progress.close()
