import xbmc

from resources.lib.settings import UI


def log(message: str, verbose: bool = False) -> None:
    if verbose and not UI.verbose:
        return
    xbmc.log(f'{self._name}: {message}')
