import os
from dataclasses import dataclass

from meme.exceptions import ConfigurationError


DEFAULT_API_URL = "https://ark.cn-beijing.volces.com/api/v3/chat/completions"
DEFAULT_MODEL = "doubao-seed-1-8-251228"
DEFAULT_PROMPT = "通过分析给出这个表情包的：所代表情绪、使用场景、设计灵感，最终以json的格式返回"
DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8000


@dataclass(frozen=True)
class APIConfig:
    api_key: str
    api_url: str = DEFAULT_API_URL
    model: str = DEFAULT_MODEL
    prompt: str = DEFAULT_PROMPT

    @classmethod
    def from_env(cls, api_key_override: str | None = None) -> "APIConfig":
        api_key = api_key_override or os.getenv("ARK_API_KEY")
        if not api_key:
            raise ConfigurationError(
                "ARK_API_KEY environment variable is required. "
                "Set it with: export ARK_API_KEY=your-api-key"
            )

        return cls(
            api_key=api_key,
            api_url=os.getenv("ARK_API_URL", DEFAULT_API_URL),
            model=os.getenv("ARK_MODEL", DEFAULT_MODEL),
            prompt=os.getenv("ARK_PROMPT", DEFAULT_PROMPT),
        )


@dataclass(frozen=True)
class ServerConfig:
    host: str = DEFAULT_HOST
    port: int = DEFAULT_PORT

    @classmethod
    def from_env(cls) -> "ServerConfig":
        return cls(
            host=os.getenv("ANALYSIS_HOST", DEFAULT_HOST),
            port=int(os.getenv("ANALYSIS_PORT", str(DEFAULT_PORT))),
        )
