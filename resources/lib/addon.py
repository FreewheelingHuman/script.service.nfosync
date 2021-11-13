from typing import Final, Optional

import xbmcaddon

import resources.lib.utcdt as utcdt


class Settings:

    def __init__(self):
        self.manual: Final = self._Manual()
        self.start: Final = self._Start()
        self.periodic: Final = self._Periodic()
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
            return ADDON.getSettingInt('periodic.period')

        @property
        def avoid_play(self) -> bool:
            return ADDON.getSettingBool('periodic.avoid_play')

        @property
        def wait(self) -> int:
            return ADDON.getSettingInt('periodic.wait')

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
        def last_refresh(self, value: utcdt.Dt) -> None:
            ADDON.setSetting(self._last_refresh, value.isoformat(timespec='seconds'))


ADDON: Final = xbmcaddon.Addon()
ADDON_ID: Final = ADDON.getAddonInfo('id')
SETTINGS: Final = Settings()
