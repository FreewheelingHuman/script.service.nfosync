import resources.lib.jsonrpc as jsonrpc
from resources.lib.addon import addon


jsonrpc.request(
    'JSONRPC.NotifyAll',
    sender=addon.id,
    message=jsonrpc.INTERNAL_METHODS.immediate_sync.send,
)
