import json
from typing import Final

import xbmc

from resources.lib.addon import addon


class _InternalMethods:
    class _Method:
        def __init__(self, method: str):
            self._method = f'{addon.json_name}.{method}'

        @property
        def send(self) -> str:
            return self._method

        @property
        def recv(self) -> str:
            return 'Other.' + self._method

    sync_all: Final = _Method('SyncAll')
    sync_one: Final = _Method('SyncOne')
    import_all: Final = _Method('ImportAll')
    export_one: Final = _Method('Export')
    export_all: Final = _Method('ExportAll')
    wait_done: Final = _Method('WaitDone')


INTERNAL_METHODS: Final = _InternalMethods()


class RequestError(Exception):
    pass


def request(method: str, **params) -> dict:
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

    return response['result']


def notify(message: str, data: dict = None) -> None:
    notification = {
        'sender': addon.id,
        'message': message
    }
    if data:
        notification['data'] = data

    request(
        'JSONRPC.NotifyAll',
        **notification
    )
