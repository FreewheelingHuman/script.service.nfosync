import sys

import resources.lib.jsonrpc as jsonrpc
from resources.lib.addon import addon


def sync_all(arguments: list):
    del arguments
    jsonrpc.notify(message=jsonrpc.INTERNAL_METHODS.immediate_sync.send)


def patient_sync(arguments: list):
    del arguments
    jsonrpc.notify(message=jsonrpc.INTERNAL_METHODS.patient_sync_sync.send)


def sync_one(arguments: list):
    if len(arguments) < 2:
        addon.log('Script - sync_one is missing arguments. Requires: media type, library id')
        addon.notify(32074)
        return

    jsonrpc.notify(
        message=jsonrpc.INTERNAL_METHODS.sync_one.send,
        data={'type': arguments[0], 'id': arguments[1]}
    )


def import_all(arguments: list):
    del arguments
    jsonrpc.notify(message=jsonrpc.INTERNAL_METHODS.import_all.send)


def export(arguments: list):
    if len(arguments) < 2:
        addon.log('Script - export is missing arguments. Requires: media type, library id')
        addon.notify(32074)
        return

    jsonrpc.notify(
        message=jsonrpc.INTERNAL_METHODS.export.send,
        data={'type': arguments[0], 'id': arguments[1]}
    )


def export_all(arguments: list):
    del arguments
    jsonrpc.notify(message=jsonrpc.INTERNAL_METHODS.export_all.send)


functions = {
    'sync_one': sync_one,
    'sync_all': sync_all,
    'import_all': import_all,
    'export_one': export,
    'export_all': export_all
}

addon.log(f'Script - Running with parameters: {sys.argv}')

try:
    command = sys.argv[1]
except IndexError:
    command = 'sync'

functions[command](sys.argv[2:])
