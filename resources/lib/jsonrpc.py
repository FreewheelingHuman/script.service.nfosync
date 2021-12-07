import json
from typing import Final

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


class RequestError(Exception):
    pass


def request(method: str, **params) -> (dict, str):
    contents = {
        'jsonrpc': '2.0',
        'method': method,
        'params': params,
        'id': 1
    }
    raw_response = xbmc.executeJSONRPC(json.dumps(contents))
    response = json.loads(raw_response)
    if 'error' in response:
        raise RequestError(f'JSONRPC request failed.\nRequest: {contents}\nResponse: {response}')

    return response['result'], raw_response
