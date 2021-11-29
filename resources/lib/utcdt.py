import datetime
import typing


UtcDt = typing.NewType('UtcDt', datetime.datetime)


def fromisoformat(date_string: str) -> UtcDt:
    naive_dt = datetime.datetime.fromisoformat(date_string)
    utc_dt = naive_dt.astimezone(datetime.timezone.utc)
    return typing.cast(UtcDt, utc_dt)


def fromtimestamp(timestamp: float) -> UtcDt:
    dt = datetime.datetime.fromtimestamp(timestamp, tz=datetime.timezone.utc)
    return typing.cast(UtcDt, dt)


def now() -> UtcDt:
    dt = datetime.datetime.now(datetime.timezone.utc)
    return typing.cast(UtcDt, dt)
