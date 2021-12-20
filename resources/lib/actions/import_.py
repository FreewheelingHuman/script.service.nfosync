import xbmcgui

import resources.lib.jsonrpc as jsonrpc
import resources.lib.media as media
from resources.lib.addon import addon

from . import *


class _DialogCancelled(Exception):
    pass


class ImportOne(Action):

    type = 'Import One'

    def __init__(self, info: media.MediaInfo):
        super().__init__()
        self._info = info

    def run(self) -> None:
        addon.log(f'Import - A refresh has been requested for "{self._info.details["title"]}"', verbose=True)
        jsonrpc.request(
            media.TYPE_INFO[self._info.type].refresh_method,
            **{media.TYPE_INFO[self._info.type].id_name: self._info.id}
        )

        # Prevent import requests from stacking up - Kodi won't respond to this until all previous requests
        # are already being processed (though not necessarily done)
        jsonrpc.request('JSONRPC.Ping')


class ImportAll(Action):

    type = 'Import All'

    def run(self) -> None:
        dialog = xbmcgui.DialogProgress()
        dialog.create(addon.getLocalizedString(32065))

        def import_type(type_: str, message: int, fraction: int, base_progress: int) -> None:
            type_info = media.TYPE_INFO[type_]

            items = media.get_all(type_)
            count = 0
            total = len(items)
            for item in items:
                ImportOne(media.MediaInfo(type_, item[type_info.id_name], file=item['file'])).run()
                if dialog.iscanceled():
                    raise _DialogCancelled
                count += 1
                progress = int(count / total * fraction) + base_progress
                dialog.update(progress, addon.getLocalizedString(message))

        try:
            import_type(type_='movie', message=32066, fraction=33, base_progress=0)
            import_type(type_='tvshow', message=32067, fraction=33, base_progress=33)
            import_type(type_='episode', message=32068, fraction=34, base_progress=66)

        except _DialogCancelled:
            pass

        finally:
            dialog.close()
