import json
from typing import Final, Optional

import xbmc
import xbmcaddon

import resources.lib.utcdt as utcdt


ADDON: Final = xbmcaddon.Addon()
ADDON_ID: Final = ADDON.getAddonInfo('id')
PLAYER: Final = xbmc.Player()


class Settings:

    def __init__(self):
        self.manual: Final = self._Manual()
        self.start: Final = self._Start()
        self.periodic: Final = self._Periodic()
        self.export: Final = self._AutoExport()
        self.state: Final = self._State()

    class _ActionGroup:
        _visible = None
        _clean = None
        _refresh = None
        _scan = None

        @property
        def visible(self) -> bool:
            return ADDON.getSettingBool(self._visible)

        @property
        def clean(self) -> bool:
            return ADDON.getSettingBool(self._clean)

        @property
        def refresh(self) -> bool:
            return ADDON.getSettingBool(self._refresh)

        @property
        def scan(self) -> bool:
            return ADDON.getSettingBool(self._scan)

    class _SwitchableActionGroup(_ActionGroup):
        _enabled = None

        @property
        def enabled(self) -> bool:
            return ADDON.getSettingBool(self._enabled)

    class _Manual(_ActionGroup):
        _visible: Final = 'manual.visible'
        _clean: Final = 'manual.clean'
        _refresh: Final = 'manual.refresh'
        _scan: Final = 'manual.scan'

    class _Start(_SwitchableActionGroup):
        _enabled: Final = 'on_start.enabled'
        _visible: Final = 'on_start.visible'
        _clean: Final = 'on_start.clean'
        _refresh: Final = 'on_start.refresh'
        _scan: Final = 'on_start.scan'

    class _Periodic(_SwitchableActionGroup):
        _enabled: Final = 'periodic.enabled'
        _visible: Final = 'periodic.visible'
        _clean: Final = 'periodic.clean'
        _refresh: Final = 'periodic.refresh'
        _scan: Final = 'periodic.scan'

        @property
        def period(self) -> int:
            if self.enabled:
                return ADDON.getSettingInt('periodic.period') * 60
            else:
                return 0

        @property
        def avoid_play(self) -> bool:
            return ADDON.getSettingBool('periodic.avoid_play')

        @property
        def wait(self) -> int:
            if self.avoid_play:
                return ADDON.getSettingInt('periodic.wait')
            else:
                return 0

    class _AutoExport:
        _enabled: Final = 'auto_export.enabled'
        _create: Final = 'auto_export.create'
        _ignore_added: Final = 'auto_export.ignore_added'

        @property
        def enabled(self) -> bool:
            return ADDON.getSettingBool(self._enabled)

        @property
        def create(self) -> bool:
            return ADDON.getSettingBool(self._create)

        @property
        def ignore_added(self) -> bool:
            return ADDON.getSettingBool(self._ignore_added)

    class _State:
        _last_refresh: Final = 'state.last_refresh'

        class _RefreshExceptions:
            _refresh_exceptions: Final = 'state.refresh_exceptions'

            def __init__(self):
                self._cache = json.loads(ADDON.getSettingString(self._refresh_exceptions))

            def __getitem__(self, file: str) -> utcdt.Dt:
                return utcdt.fromisoformat(self._cache[file])

            def __setitem__(self, file: str, timestamp: utcdt.Dt) -> None:
                self._cache[file] = timestamp.isoformat(timespec='seconds')
                ADDON.setSettingString(self._refresh_exceptions, json.dumps(self._cache))

            def clear(self) -> None:
                self._cache = {}
                ADDON.setSettingString(self._refresh_exceptions, '{}')

        def __init__(self):
            self._refresh_exceptions_wrapper: Final = self._RefreshExceptions()

        @property
        def last_refresh(self) -> Optional[utcdt.Dt]:
            iso_string = ADDON.getSetting(self._last_refresh)
            if iso_string == '':
                return None

            last_scan = utcdt.fromisoformat(iso_string)

            return last_scan

        @last_refresh.setter
        def last_refresh(self, value: utcdt.Dt) -> None:
            ADDON.setSetting(self._last_refresh, value.isoformat(timespec='seconds'))

        @property
        def refresh_exceptions(self) -> _RefreshExceptions:
            return self._refresh_exceptions_wrapper


SETTINGS: Final = Settings()
