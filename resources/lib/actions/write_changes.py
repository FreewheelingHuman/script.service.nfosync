from typing import Optional

from resources.lib.last_known import last_known

from . import *


class WriteChanges(Action):

    _type = "Write Changes"

    def run(self, data: Optional[dict] = None) -> bool:
        del data
        last_known.write_changes()
        return True
