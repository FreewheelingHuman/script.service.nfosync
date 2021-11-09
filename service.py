import xbmc
import xbmcaddon

from resources.lib.refresher import refresh


class Service(xbmc.Monitor):
    def __init__(self):
        super().__init__()

        self._addon = xbmcaddon.Addon()

        # Clear the in progress status so if a run didn't finish, a restart will at least fix it
        self._addon.setSettingBool('in_progress.active', False)

        clean = self._addon.getSettingBool('on_start.clean')
        refresh(clean=clean)

        while not self.abortRequested():
            self.waitForAbort(100)

    def onCleanFinished(self, library):
        if library == 'video' and self._addon.getSettingBool('in_progress.active'):
            refresh(clean=False)


if __name__ == "__main__":
    Service()
