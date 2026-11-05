class WordpressPublisher:
    def prepare(self, post: dict) -> dict:
        return {"platform":"wordpress","status":"MANUAL_HANDOFF" if "wordpress"=="naver" else "NOT_IMPLEMENTED","post":post}
    def publish(self, prepared: dict, approval: dict) -> dict:
        raise NotImplementedError("WordPress 인증·미디어 업로드·초안 API는 아직 연결되지 않았습니다. 자동 발행하지 않았습니다.")
