from .base import ProviderUnavailable

class NaverShoppingProvider:
    """The former public shopping search API was retired 2026-07-31."""
    def collect(self, model: str, variant: str):
        raise ProviderUnavailable("NAVER_SHOPPING_LEGACY_API_RETIRED: 허용된 별도 공급 경로를 구현해야 합니다.")
