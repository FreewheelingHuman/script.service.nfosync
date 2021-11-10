import resources.lib.jsonrpc as jsonrpc
from resources.lib.settings import Settings


settings = Settings()
jsonrpc.request(
    'JSONRPC.NotifyAll',
    sender=settings.addon_id,
    message=jsonrpc.custom_methods.refresh.send,
    data={'clean': settings.manual.clean, 'scan': settings.manual.scan}
)
