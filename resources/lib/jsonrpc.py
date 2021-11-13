import json
from typing import Final

import xbmc


class _CustomMethods:
    class _Method:
        def __init__(self, method: str):
            self._method = method

        @property
        def send(self) -> str:
            return self._method

        @property
        def recv(self) -> str:
            return 'Other.' + self._method

    import_now: Final = _Method('NFOSync.Import_Now')
    import_periodic: Final = _Method('NFOSync.Import_Periodic')
    periodic_wait_done: Final = _Method('NFOSync.Periodic_Wait_Done')


custom_methods = _CustomMethods()


def request(method: str, **params):
    contents = {
        'jsonrpc': '2.0',
        'method': method,
        'params': params,
        'id': 1
    }
    result = xbmc.executeJSONRPC(json.dumps(contents))
    return json.loads(result)['result']
