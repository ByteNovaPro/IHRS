from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any, AsyncIterator, Literal

from langchain_core.output_parsers import PydanticOutputParser, StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field, ValidationError


class LlmGenerationError(RuntimeError):
    """Raised when the configured LLM cannot produce a usable response."""


class TriageGeneration(BaseModel):
    patientSummary: str = Field(description="一句话概括患者当前描述，不超过 40 个汉字")
    departmentRecommendation: str = Field(description="首诊推荐科室，优先使用系统提供的标准科室名称")
    reason: str = Field(description="一句话说明分诊依据，尽量控制在 50 个汉字内")
    generatedAnswer: str = Field(description="3 到 4 句中文导诊回复")
    followUpQuestions: list[str] = Field(default_factory=list, description="2 到 3 个高价值追问")
    urgency: Literal["normal", "soon", "emergency"] = Field(description="就诊紧急程度")


@dataclass(frozen=True)
class LlmSettings:
    base_url: str
    model: str
    api_key: str = ""
    timeout_seconds: float = 90.0
    temperature: float = 0.2

    @property
    def enabled(self) -> bool:
        return bool(self.base_url and self.model)

    @classmethod
    def from_env(cls) -> "LlmSettings":
        return cls(
            base_url=os.getenv("LLM_BASE_URL", "").strip(),
            model=os.getenv("LLM_MODEL", "").strip(),
            api_key=os.getenv("LLM_API_KEY", "").strip(),
            timeout_seconds=float(os.getenv("LLM_TIMEOUT_SECONDS", "90").strip()),
            temperature=float(os.getenv("LLM_TEMPERATURE", "0.2").strip()),
        )


class LangChainTriageClient:
    def __init__(self, settings: LlmSettings | None = None) -> None:
        self.settings = settings or LlmSettings.from_env()
        self._json_parser = PydanticOutputParser(pydantic_object=TriageGeneration)
        self._text_parser = StrOutputParser()
        self._model = self._build_model() if self.settings.enabled else None
        self._json_prompt = ChatPromptTemplate.from_messages(
            [
                ("system", "{system_prompt}"),
                (
                    "user",
                    "{user_prompt}\n\n"
                    "请严格遵守以下输出格式说明：\n{format_instructions}",
                ),
            ]
        )
        self._text_prompt = ChatPromptTemplate.from_messages(
            [
                ("system", "{system_prompt}"),
                ("user", "{user_prompt}"),
            ]
        )

    @property
    def is_configured(self) -> bool:
        return self._model is not None

    async def generate_json(self, *, system_prompt: str, user_prompt: str) -> dict[str, Any]:
        if self._model is None:
            raise LlmGenerationError("LLM is not configured.")

        chain = self._json_prompt | self._model | self._json_parser
        try:
            result = await chain.ainvoke(
                {
                    "system_prompt": system_prompt,
                    "user_prompt": user_prompt,
                    "format_instructions": self._json_parser.get_format_instructions(),
                }
            )
        except (ValidationError, ValueError) as exc:
            raise LlmGenerationError("LLM returned invalid structured content.") from exc
        except Exception as exc:
            raise LlmGenerationError(f"LangChain generation failed: {exc}") from exc

        return result.model_dump()

    async def stream_text(self, *, system_prompt: str, user_prompt: str) -> AsyncIterator[str]:
        if self._model is None:
            raise LlmGenerationError("LLM is not configured.")

        chain = self._text_prompt | self._model | self._text_parser
        try:
            async for chunk in chain.astream(
                {
                    "system_prompt": system_prompt,
                    "user_prompt": user_prompt,
                }
            ):
                if chunk:
                    yield chunk
        except Exception as exc:
            raise LlmGenerationError(f"LangChain streaming failed: {exc}") from exc

    def _build_model(self) -> ChatOpenAI:
        return ChatOpenAI(
            model=self.settings.model,
            api_key=self.settings.api_key or "not-needed",
            base_url=self._normalize_base_url(self.settings.base_url),
            timeout=self.settings.timeout_seconds,
            temperature=self.settings.temperature,
        )

    def _normalize_base_url(self, value: str) -> str:
        normalized = value.strip().rstrip("/")
        suffix = "/chat/completions"
        if normalized.endswith(suffix):
            return normalized[: -len(suffix)]
        return normalized

OpenAICompatibleLlmClient = LangChainTriageClient
