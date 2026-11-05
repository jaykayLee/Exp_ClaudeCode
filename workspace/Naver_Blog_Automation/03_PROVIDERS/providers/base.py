from __future__ import annotations
from typing import Protocol
from dataclasses import dataclass

@dataclass(frozen=True)
class PriceCandidate:
    provider: str
    product_id: str
    model: str
    variant: str
    price: int
    url: str
    observed_at: str
    price_basis: str
    image_url: str | None = None

class PriceProvider(Protocol):
    def collect(self, model: str, variant: str) -> list[PriceCandidate]: ...

class ProviderUnavailable(RuntimeError):
    pass
