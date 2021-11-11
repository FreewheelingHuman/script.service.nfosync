import resources.lib.jsonrpc as jsonrpc
from resources.lib.addon import ADDON_ID, SETTINGS


jsonrpc.request(
    'JSONRPC.NotifyAll',
    sender=ADDON_ID,
    message=jsonrpc.custom_methods.refresh.send,
    data={'clean': SETTINGS.manual.clean, 'scan': SETTINGS.manual.scan}
)
