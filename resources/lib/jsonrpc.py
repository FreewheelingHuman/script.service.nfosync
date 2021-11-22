import json
from typing import Final

import xbmc


class _InternalMethods:
    class _Method:
        def __init__(self, method: str):
            self._method = method

        @property
        def SEND(self) -> str:
            return self._method

        @property
        def RECV(self) -> str:
            return 'Other.' + self._method

    IMMEDIATE_SYNC: Final = _Method('NFOSync.Immediate_Sync')
    PATIENT_SYNC: Final = _Method('NFOSync.Patient_Sync')
    WAIT_DONE: Final = _Method('NFOSync.Wait_Done')


Internal_Methods: Final = _InternalMethods()


def request(method: str, **params):
    contents = {
        'jsonrpc': '2.0',
        'method': method,
        'params': params,
        'id': 1
    }
    result = xbmc.executeJSONRPC(json.dumps(contents))
    return json.loads(result)['result']
