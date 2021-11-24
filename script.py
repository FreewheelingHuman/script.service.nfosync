import resources.lib.jsonrpc as jsonrpc
from resources.lib.addon import ADDON


jsonrpc.request(
    'JSONRPC.NotifyAll',
    sender=ADDON.id,
    message=jsonrpc.INTERNAL_METHODS.immediate_sync.send,
)
