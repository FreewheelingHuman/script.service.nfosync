from typing import Optional


class Action:

    _type = 'Action'

    def __init__(self, **kwargs):
        self._awaiting = None

    @property
    def awaiting(self) -> Optional[str]:
        return self._awaiting

    @property
    def is_done(self) -> bool:
        if self._awaiting is None:
            return True
        return False

    @property
    def type(self) -> str:
        return self._type

    def run(self) -> None:
        pass
