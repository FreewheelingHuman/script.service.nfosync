import json
from typing import Final, Optional

import xbmc

from resources.lib.addon import ADDON
from resources.lib.log import log


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

    immediate_sync: Final = _Method(f'{ADDON.json_name}.Immediate_Sync')
    patient_sync: Final = _Method(f'{ADDON.json_name}.Patient_Sync')
    wait_done: Final = _Method(f'{ADDON.json_name}.Wait_Done')


INTERNAL_METHODS = _InternalMethods()


def request(method: str, **params) -> Optional[dict]:
    contents = {
        'jsonrpc': '2.0',
        'method': method,
        'params': params,
        'id': 1
    }
    response = json.loads(xbmc.executeJSONRPC(json.dumps(contents)))
    if 'error' in response:
        log(f'JSONRPC request failed.\nRequest: {contents}\nResponse: {response}')

    return response.get('result', None)

