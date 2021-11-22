import resources.lib.jsonrpc as jsonrpc
from resources.lib.addon import ADDON_ID


jsonrpc.request(
    'JSONRPC.NotifyAll',
    sender=ADDON_ID,
    message=jsonrpc.INTERNAL_METHODS.immediate_sync.send,
)
