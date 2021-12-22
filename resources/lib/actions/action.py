from typing import Final, Iterator, Optional


class Action:

    _type = '[Action]'

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

    def run(self, data: Optional[dict] = None) -> bool:
        return True


class ActionError(Exception):

    def __init__(self, notification: int, message: str):
        super().__init__(message)
        self.notification: Final = notification


class _RequestResponseAction(Action):

    _type = '[Request-Response Action]'

    def run(self, data: Optional[dict] = None) -> bool:
        del data
        if self._awaiting:
            self._awaiting = None
            return True
        self._request()

    def _request(self):
        return


class _PhasedAction(Action):

    _type = '[Phased Action]'

    def __init__(self):
        super().__init__()
        self._active_phase = None
        self._future_phases = self._phases()

    def run(self, data: Optional[dict] = None) -> bool:
        try:
            return self._run_phases(data)
        except Exception as error:
            self._awaiting = None
            self._cleanup()
            raise error

    def _run_phases(self, data: Optional[dict] = None) -> bool:
        while True:
            if not self._active_phase:
                try:
                    self._active_phase = next(self._future_phases)
                except StopIteration:
                    self._cleanup()
                    return True

            try:
                self._active_phase.run(data)
            except ActionError as error:
                self._exception(error)

            if not self._active_phase.is_done:
                self._awaiting = self._active_phase.awaiting
                return True
            self._active_phase = None
            self._awaiting = None
            data = None

    def _phases(self) -> Iterator[Action]:
        return iter(())

    def _cleanup(self) -> None:
        pass

    def _exception(self, error: Exception) -> None:
        raise error
