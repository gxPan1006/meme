class MemeAnalysisError(Exception):
    pass


class ConfigurationError(MemeAnalysisError):
    pass


class APIError(MemeAnalysisError):
    def __init__(
        self,
        message: str,
        status_code: int | None = None,
        response: str | None = None,
    ) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.response = response


class ImageFetchError(MemeAnalysisError):
    def __init__(self, message: str, url: str) -> None:
        super().__init__(message)
        self.url = url
