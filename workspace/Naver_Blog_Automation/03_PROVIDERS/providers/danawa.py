from .base import ProviderUnavailable

class DanawaProvider:
    """Reserved adapter. No guessed selectors, login bypass or live requests."""
    def collect(self, model: str, variant: str):
        raise ProviderUnavailable("DANAWA_LIVE_NOT_CONFIGURED: 이용 조건 및 허용 수집 경로 확인이 먼저 필요합니다.")
