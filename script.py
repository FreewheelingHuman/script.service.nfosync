import resources.lib.jsonrpc as jsonrpc
from resources.lib.addon import ADDON_ID, SETTINGS


jsonrpc.request(
    'JSONRPC.NotifyAll',
    sender=ADDON_ID,
    message=jsonrpc.custom_methods.refresh.send,
    data={
        'visible': SETTINGS.manual.visible,
        'clean': SETTINGS.manual.clean,
        'refresh': SETTINGS.manual.refresh,
        'scan': SETTINGS.manual.scan
    }
)
