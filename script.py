import sys

import resources.lib.jsonrpc as jsonrpc
from resources.lib.addon import addon


def _sync_all(arguments: list):
    is_patient = False
    if arguments:
        if arguments[0] != 'patient' or len(arguments) > 1:
            addon.log(f'Script - sync_all received an invalid argument: "{arguments[0]}". If present,'
                      f'the argument must be "patient".')
            addon.notify(32074)
        else:
            is_patient = True

    jsonrpc.notify(
        message=jsonrpc.INTERNAL_METHODS.sync_all.send,
        data={'patient': is_patient}
    )


def _sync_one(arguments: list):
    is_patient = False

    if len(arguments) < 2:
        addon.log(f'Script - sync_one only received {len(arguments)} arguments, but requires at least 2 '
                  f'(media type, library id, and optionally "patient").')
        addon.notify(32074)
        return

    if len(arguments) > 3:
        addon.log(f'Script - sync_one received {len(arguments)}, but '
                  f'can only take 3 (media type, library id, and optionally "patient").')
        addon.notify(32074)
        return

    if len(arguments) == 3:
        if arguments[2] != 'patient':
            addon.log(f'Script - sync_one received an invalid 3rd argument: "{arguments[2]}". '
                      f'If present, the 3rd argument must be "patient".')
            addon.notify(32074)
            return
        else:
            is_patient = True

    jsonrpc.notify(
        message=jsonrpc.INTERNAL_METHODS.sync_one.send,
        data={'type': arguments[0], 'id': arguments[1], 'patient': is_patient}
    )


def _import_all(arguments: list):
    is_patient = False
    if arguments:
        if arguments[0] != 'patient' or len(arguments) > 1:
            addon.log(f'Script - import_all received an invalid argument: "{arguments[0]}". If present,'
                      f'the argument must be "patient".')
            addon.notify(32074)
        else:
            is_patient = True

    jsonrpc.notify(
        message=jsonrpc.INTERNAL_METHODS.import_all.send,
        data={'patient': is_patient}
    )


def _export_one(arguments: list):
    is_patient = False

    if len(arguments) < 2:
        addon.log(f'Script - export_one only received {len(arguments)} arguments, but requires at least 2 '
                  f'(media type, library id, and optionally "patient").')
        addon.notify(32074)
        return

    if len(arguments) > 3:
        addon.log(f'Script - export_one received {len(arguments)}, but '
                  f'can only take 3 (media type, library id, and optionally "patient").')
        addon.notify(32074)
        return

    if len(arguments) == 3:
        if arguments[2] != 'patient':
            addon.log(f'Script - export_one received an invalid 3rd argument: "{arguments[2]}". '
                      f'If present, the 3rd argument must be "patient".')
            addon.notify(32074)
            return
        else:
            is_patient = True

    jsonrpc.notify(
        message=jsonrpc.INTERNAL_METHODS.export_one.send,
        data={'type': arguments[0], 'id': arguments[1], 'patient': is_patient}
    )


def _export_all(arguments: list):
    is_patient = False
    if arguments:
        if arguments[0] != 'patient' or len(arguments) > 1:
            addon.log(f'Script - export_all received an invalid argument: "{arguments[0]}". If present,'
                      f'the argument must be "patient".')
            addon.notify(32074)
        else:
            is_patient = True

    jsonrpc.notify(
        message=jsonrpc.INTERNAL_METHODS.export_all.send,
        data={'patient': is_patient}
    )


functions = {
    'sync_one': _sync_one,
    'sync_all': _sync_all,
    'import_all': _import_all,
    'export_one': _export_one,
    'export_all': _export_all
}

addon.log(f'Script - Running with parameters: {sys.argv}', verbose=True)

command = 'sync_all'
if len(sys.argv) > 1:
    command = sys.argv[1]

try:
    functions[command](sys.argv[2:])
except KeyError:
    addon.log(f'Script - Invalid command {command} provided. Valid commands: {functions.keys()}')
    addon.notify(32074)
