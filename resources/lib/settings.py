from typing import Optional

import xbmcaddon

import resources.lib.utcdt as utcdt


class Settings:

    def __init__(self):
        self._addon = xbmcaddon.Addon()

        self.addon_id: str = self._addon.getAddonInfo('id')

        self.manual = self._Manual(self._addon)
        self.start = self._Start(self._addon)
        self.state = self._State(self._addon)

    class _SubGroup:
        def __init__(self, addon: xbmcaddon.Addon):
            self._addon = addon

    class _ActionGroup(_SubGroup):
        _clean = None
        _scan = None

        @property
        def clean(self) -> bool:
            return self._addon.getSettingBool(self._clean)

        @clean.setter
        def clean(self, value: bool) -> None:
            self._addon.setSettingBool(self._clean, value)

        @property
        def scan(self) -> bool:
            return self._addon.getSettingBool(self._scan)

        @scan.setter
        def scan(self, value: bool) -> None:
            self._addon.setSettingBool(self._scan, value)

    class _Manual(_ActionGroup):
        _clean = 'manual.clean'
        _scan = 'manual.scan'

    class _Start(_ActionGroup):
        _clean = 'on_start.clean'
        _scan = 'on_start.scan'

    class _State(_SubGroup):
        _last_scan = 'state.last_scan'

        @property
        def last_scan(self) -> Optional[utcdt.Dt]:
            iso_string = self._addon.getSetting(self._last_scan)
            if iso_string == '':
                return None

            last_scan = utcdt.fromisoformat(iso_string)

            return last_scan

        @last_scan.setter
        def last_scan(self, value: utcdt.Dt):
            self._addon.setSetting(self._last_scan, value.isoformat(timespec='seconds'))
