from typing import Optional

import xbmcaddon

import resources.lib.utcdt as utcdt


class Settings:

    def __init__(self):
        self.manual = self._Manual()
        self.start = self._Start()
        self.state = self._State()

    class _ActionGroup:
        _clean = None
        _scan = None

        @property
        def clean(self) -> bool:
            return ADDON.getSettingBool(self._clean)

        @clean.setter
        def clean(self, value: bool) -> None:
            ADDON.setSettingBool(self._clean, value)

        @property
        def scan(self) -> bool:
            return ADDON.getSettingBool(self._scan)

        @scan.setter
        def scan(self, value: bool) -> None:
            ADDON.setSettingBool(self._scan, value)

    class _Manual(_ActionGroup):
        _clean = 'manual.clean'
        _scan = 'manual.scan'

    class _Start(_ActionGroup):
        _clean = 'on_start.clean'
        _scan = 'on_start.scan'

    class _State:
        _last_refresh = 'state.last_refresh'

        @property
        def last_refresh(self) -> Optional[utcdt.Dt]:
            iso_string = ADDON.getSetting(self._last_refresh)
            if iso_string == '':
                return None

            last_scan = utcdt.fromisoformat(iso_string)

            return last_scan

        @last_refresh.setter
        def last_refresh(self, value: utcdt.Dt):
            ADDON.setSetting(self._last_refresh, value.isoformat(timespec='seconds'))


ADDON = xbmcaddon.Addon()
ADDON_ID = ADDON.getAddonInfo('id')
SETTINGS = Settings()
