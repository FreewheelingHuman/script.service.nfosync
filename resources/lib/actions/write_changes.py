from resources.lib.last_known import last_known

from . import *


class WriteChanges(Action):

    _type = "Write Changes"

    def run(self):
        last_known.write_changes()
