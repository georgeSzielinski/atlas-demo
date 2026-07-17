from dataclasses import dataclass

@dataclass
class WatchlistItem:
    ticker: str
    target_price: float
    notes: str = ""