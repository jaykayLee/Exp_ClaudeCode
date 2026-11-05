class NaverPublisher:
    def prepare(self, post: dict) -> dict:
        return {"platform":"naver","status":"MANUAL_HANDOFF" if "naver"=="naver" else "NOT_IMPLEMENTED","post":post}
    def publish(self, prepared: dict, approval: dict) -> dict:
        raise NotImplementedError("수동 게시 준비만 지원합니다. 자동 발행하지 않았습니다.")
