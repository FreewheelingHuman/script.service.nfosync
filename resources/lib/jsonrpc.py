import json
from typing import Final

import xbmc


class _InternalMethods:
    class _Method:
        def __init__(self, method: str):
            self._method = method

        @property
        def send(self) -> str:
            return self._method

        @property
        def recv(self) -> str:
            return 'Other.' + self._method

    immediate_sync: Final = _Method('NFOSync.Immediate_Sync')
    patient_sync: Final = _Method('NFOSync.Patient_Sync')
    wait_over: Final = _Method('NFOSync.Wait_Over')


INTERNAL_METHODS = _InternalMethods()


def request(method: str, **params):
    contents = {
        'jsonrpc': '2.0',
        'method': method,
        'params': params,
        'id': 1
    }
    result = xbmc.executeJSONRPC(json.dumps(contents))
    return json.loads(result)['result']
