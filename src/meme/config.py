import os
from dataclasses import dataclass

from dotenv import load_dotenv

from meme.exceptions import ConfigurationError


load_dotenv()


DEFAULT_API_URL = "https://ark.cn-beijing.volces.com/api/v3/chat/completions"
DEFAULT_MODEL = "doubao-seed-1-8-251228"
DEFAULT_PROMPT = (
    "请分析这个表情包并返回JSON，包含字段：所代表情绪、使用场景、设计灵感。"
    "只输出JSON，不要附加解释或Markdown。"
)
DEFAULT_INSTRUCT_PROMPT = (
    "请根据此图片和用户的需求给出一个表情包的生成策略，纯文本，以便后续以此策略去设计表情包，包含字段：所代表情绪、使用场景、设计灵感。"
)
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
