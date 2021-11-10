import datetime
import typing


Dt = typing.NewType('Dt', datetime.datetime)


def fromisoformat(date_string: str) -> Dt:
    dt = datetime.datetime.fromisoformat(date_string)
    dt = dt.replace(tzinfo=datetime.timezone.utc)
    return typing.cast(Dt, dt)


def fromtimestamp(timestamp: float) -> Dt:
    dt = datetime.datetime.fromtimestamp(timestamp, tz=datetime.timezone.utc)
    return typing.cast(Dt, dt)


def now() -> Dt:
    dt = datetime.datetime.now(datetime.timezone.utc)
    return typing.cast(Dt, dt)
