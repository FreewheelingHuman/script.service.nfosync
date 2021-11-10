# import datetime
from typing import Optional

import xbmcaddon

import resources.lib.utcdt as utcdt


class Settings:

    def __init__(self):
        self._addon = xbmcaddon.Addon()
        self.manual = self.Manual(self._addon)
        self.start = self.Start(self._addon)
        self.in_progress = self.InProgress(self._addon)
        self.state = self.State(self._addon)

    class SubGroup:
        def __init__(self, addon: xbmcaddon.Addon):
            self._addon = addon

    class ActionGroup(SubGroup):
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

    class Manual(ActionGroup):
        _clean = 'manual.clean'
        _scan = 'manual.scan'

    class Start(ActionGroup):
        _clean = 'on_start.clean'
        _scan = 'on_start.scan'

    class InProgress(ActionGroup):
        _active = 'in_progress.active'
        _scan = 'in_progress.scan'

        @property
        def active(self) -> bool:
            return self._addon.getSettingBool(self._active)

        @active.setter
        def active(self, value: bool):
            self._addon.setSettingBool(self._active, value)

        @property
        def clean(self) -> bool:
            return False

        @clean.setter
        def clean(self, value: bool):
            raise RuntimeError('Clean value cannot be set for the in_progress action group.')

    class State(SubGroup):
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
