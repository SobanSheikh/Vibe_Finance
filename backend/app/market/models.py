from dataclasses import dataclass
from datetime import date
from typing import Protocol


@dataclass(frozen=True)
class MarketBar:
    trading_date: date
    close: float
    volume: int


class MarketDataError(RuntimeError):
    """A provider could not return valid market observations."""


class MarketDataProvider(Protocol):
    name: str

    def history(self, symbol: str, exchange: str) -> list[MarketBar]: ...
