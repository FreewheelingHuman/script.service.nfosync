import json

import xbmc


def jsonrpc(method, **params):
    request = {
        "jsonrpc": "2.0",
        "method": method,
        "params": params,
        "id": 1
    }
    result = xbmc.executeJSONRPC(json.dumps(request))
    return json.loads(result)
