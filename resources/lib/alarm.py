import json
from typing import Optional, Final

import xbmc

import resources.lib.jsonrpc as jsonrpc
from resources.lib.addon import addon


class Alarm(xbmc.Monitor):
    def __init__(self, name: str, message: str, data: Optional[dict] = None, loop: bool = False):
        super().__init__()

        self._name: Final = f'{addon.id}.{name}'
        self._command: Final = f'NotifyAll({addon.id},{jsonrpc.INTERNAL_METHODS.alarm.send},{{"name":"{self._name}"}})'
        self._loop: Final = ',loop' if loop else ''

        self._message = message
        self._data = data

        self._minutes = 0

    @property
    def is_active(self) -> bool:
        return bool(self._minutes)

    @property
    def minutes(self) -> int:
        return self._minutes

    def set(self, minutes):
        self.cancel()
        if minutes > 0:
            self._minutes = minutes
            xbmc.executebuiltin(f'AlarmClock({self._name},{self._command},{self._minutes},silent{self._loop})')

    def cancel(self):
        xbmc.executebuiltin(f'CancelAlarm({self._name},silent)')
        self._minutes = 0

    def onNotification(self, sender: str, method: str, data: str) -> None:
        if method != jsonrpc.INTERNAL_METHODS.alarm.recv:
            return
        data = json.loads(data)
        addon.log(f'Alarm Notification: {data}')
        if data['name'] != self._name:
            return

        if self._data:
            jsonrpc.notify(message=self._message, data=self._data)
        else:
            jsonrpc.notify(message=self._message)

        if not self._loop:
            self._minutes = 0
