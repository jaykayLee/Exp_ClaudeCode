class BloggerPublisher:
    def prepare(self, post: dict) -> dict:
        return {"platform":"blogger","status":"MANUAL_HANDOFF" if "blogger"=="naver" else "NOT_IMPLEMENTED","post":post}
    def publish(self, prepared: dict, approval: dict) -> dict:
        raise NotImplementedError("Blogger OAuth·이미지 호스팅·초안 API는 아직 연결되지 않았습니다. 자동 발행하지 않았습니다.")
