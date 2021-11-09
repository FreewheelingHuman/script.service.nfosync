import datetime

import xbmcaddon


class Settings:

    def __init__(self):
        self._addon = xbmcaddon.Addon()
        self.manual = self.Manual(self._addon)
        self.start = self.Start(self._addon)
        self.in_progress = self.InProgress(self._addon)
        self.state = self.State(self._addon)

    class SubGroup:
        def __init__(self, addon):
            self._addon = addon

    class ActionGroup(SubGroup):
        _clean = None

        @property
        def clean(self):
            return self._addon.getSettingBool(self._clean)

        @clean.setter
        def clean(self, value):
            self._addon.setSettingBool(self._clean, value)

    class Manual(ActionGroup):
        _clean = 'manual.clean'

    class Start(ActionGroup):
        _clean = 'on_start.clean'

    class InProgress(ActionGroup):
        _active = 'in_progress.active'

        @property
        def active(self):
            return self._addon.getSettingBool(self._active)

        @active.setter
        def active(self, value):
            self._addon.setSettingBool(self._active, value)

        @property
        def clean(self):
            return False

        @clean.setter
        def clean(self, value):
            raise RuntimeError('Clean value cannot be set for the in_progress action group.')

    class State(SubGroup):
        _last_scan = 'state.last_scan'

        @property
        def last_scan(self):
            iso_string = self._addon.getSetting(self._last_scan)
            if iso_string == '':
                return None

            last_scan = datetime.datetime.fromisoformat(iso_string)
            last_scan.replace(tzinfo=datetime.timezone.utc)

            return last_scan

        @last_scan.setter
        def last_scan(self, value):
            self._addon.setSetting(self._last_scan, value.isoformat(timespec='seconds'))
