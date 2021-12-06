import json
from typing import Final, Optional

import xbmc

from resources.lib.addon import addon


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

    immediate_sync: Final = _Method(f'{addon.json_name}.Immediate_Sync')
    patient_sync: Final = _Method(f'{addon.json_name}.Patient_Sync')
    wait_done: Final = _Method(f'{addon.json_name}.Wait_Done')


INTERNAL_METHODS: Final = _InternalMethods()


def request(method: str, allow_failure: bool = False, **params) -> (Optional[dict], str):
    contents = {
        'jsonrpc': '2.0',
        'method': method,
        'params': params,
        'id': 1
    }
    raw_response = xbmc.executeJSONRPC(json.dumps(contents))
    response = json.loads(raw_response)
    if 'error' in response and not allow_failure:
        addon.log(f'JSONRPC request failed.\nRequest:\n{contents}\nResponse:{response}', verbose=True)

    return response.get('result', None), raw_response
