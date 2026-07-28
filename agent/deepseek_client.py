"""最小化的 DeepSeek JSON 客户端，不记录或暴露 API Key。"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


class DeepSeekError(RuntimeError):
    """DeepSeek 请求或响应不可用时抛出的脱敏错误。"""


@dataclass(frozen=True)
class DeepSeekClient:
    api_key: str
    base_url: str = "https://api.deepseek.com"
    model: str = "deepseek-v4-flash"
    timeout_seconds: float = 8.0

    @classmethod
    def from_environment(cls) -> "DeepSeekClient":
        api_key = os.getenv("DEEPSEEK_API_KEY", "").strip()
        if not api_key:
            raise DeepSeekError("未配置 DeepSeek API。")
        return cls(
            api_key=api_key,
            base_url=os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com").strip(),
            model=os.getenv("DEEPSEEK_MODEL", "deepseek-v4-flash").strip(),
        )

    def complete_json(self, system_prompt: str, user_prompt: str) -> dict:
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "response_format": {"type": "json_object"},
            "thinking": {"type": "disabled"},
            "temperature": 1.0,
            "max_tokens": 80,
            "stream": False,
        }
        request = Request(
            f"{self.base_url.rstrip('/')}/chat/completions",
            data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        try:
            with urlopen(request, timeout=self.timeout_seconds) as response:
                response_data = json.loads(response.read().decode("utf-8"))
        except HTTPError as error:
            raise DeepSeekError(f"DeepSeek HTTP {error.code}。") from None
        except (URLError, TimeoutError, OSError, json.JSONDecodeError):
            raise DeepSeekError("DeepSeek 请求失败。") from None

        try:
            content = response_data["choices"][0]["message"]["content"]
            decision = json.loads(content)
        except (KeyError, IndexError, TypeError, json.JSONDecodeError):
            raise DeepSeekError("DeepSeek 未返回有效 JSON 决策。") from None
        if not isinstance(decision, dict):
            raise DeepSeekError("DeepSeek 决策格式错误。")
        return decision
