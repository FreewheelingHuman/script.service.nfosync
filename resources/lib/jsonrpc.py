import json

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

    import_now = _Method('NFOSync.Import_Now')
    import_wait = _Method('NFOSync.Import_Wait')


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
