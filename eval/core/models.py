"""
Evaluation data models using Pydantic.

Following intent_system/core/intent_definition.py pattern.
"""

from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, field_validator


class LLMProvider(str, Enum):
    """LLM provider enumeration."""

    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    CUSTOM = "custom"


class MetricType(str, Enum):
    """Metric type enumeration."""

    ACCURACY = "accuracy"
    RELEVANCE = "relevance"
    COHERENCE = "coherence"
    CUSTOM = "custom"


class LLMConfig(BaseModel):
    """
    LLM configuration.

    Supports both 'sk' and 'api_key' for flexibility.
    """

    sk: Optional[str] = Field(default=None, description="API key (alias)")
    api_key: Optional[str] = Field(default=None, description="API key")
    base_url: Optional[str] = Field(default=None, description="LLM API endpoint")
    model_name: str = Field(default="gpt-4o", description="Model name")
    provider: LLMProvider = Field(default=LLMProvider.OPENAI, description="LLM provider")
    temperature: float = Field(default=0.0, ge=0.0, le=2.0, description="Temperature")
    max_tokens: Optional[int] = Field(default=None, ge=1, description="Max tokens")
    timeout: int = Field(default=30, ge=1, description="Request timeout (seconds)")

    def get_api_key(self) -> Optional[str]:
        """Get API key from either field."""
        return self.api_key or self.sk


class PromptConfig(BaseModel):
    """
    Prompt configuration.

    Supports HTTP-based prompt templates.
    """

    prompt_url: Optional[str] = Field(
        default=None, description="HTTP URL to fetch prompt template"
    )
    prompt_template: Optional[str] = Field(
        default=None, description="Inline prompt template (used if prompt_url not provided)"
    )
    prompt_headers: Dict[str, str] = Field(
        default_factory=dict, description="HTTP headers for prompt_url request"
    )
    cache_enabled: bool = Field(default=True, description="Enable prompt template caching")

    @field_validator("prompt_url")
    @classmethod
    def validate_prompt_url(cls, v: Optional[str]) -> Optional[str]:
        """Validate prompt URL format."""
        if v and not (v.startswith("http://") or v.startswith("https://")):
            raise ValueError("prompt_url must start with http:// or https://")
        return v


class MetricConfig(BaseModel):
    """
    Metric configuration.
    """

    name: str = Field(description="Metric name")
    type: MetricType = Field(description="Metric type")
    weight: float = Field(default=1.0, ge=0.0, description="Metric weight in scoring")
    threshold: Optional[float] = Field(
        default=None, ge=0.0, le=1.0, description="Pass threshold (0-1)"
    )
    params: Dict[str, Any] = Field(
        default_factory=dict, description="Metric-specific parameters"
    )


class EvaluationConfig(BaseModel):
    """
    Main evaluation configuration.

    This is the top-level config loaded from YAML.
    """

    name: str = Field(description="Evaluation name")
    description: Optional[str] = Field(default=None, description="Evaluation description")

    # LLM configuration
    llm: LLMConfig = Field(description="LLM configuration")

    # Prompt configuration
    prompt: PromptConfig = Field(description="Prompt configuration")

    # Metrics configuration
    metrics: List[MetricConfig] = Field(default_factory=list, description="Evaluation metrics")

    # Dataset configuration
    dataset_path: Optional[str] = Field(
        default=None, description="Path to dataset file (JSON/YAML)"
    )

    # Execution configuration
    parallel: bool = Field(default=False, description="Enable parallel evaluation")
    max_concurrent: int = Field(default=5, ge=1, description="Max concurrent evaluations")
    output_format: str = Field(default="json", description="Output format (json/csv/html)")

    # Advanced configuration
    retry_count: int = Field(default=0, ge=0, description="Retry count on failure")
    enable_cache: bool = Field(default=True, description="Enable result caching")
    verbose: bool = Field(default=False, description="Enable verbose logging")


class EvaluationResult(BaseModel):
    """
    Single evaluation result.
    """

    input: Any = Field(description="Input data")
    output: Any = Field(description="Model output")
    expected: Optional[Any] = Field(default=None, description="Expected output")

    # Metric scores
    scores: Dict[str, float] = Field(
        default_factory=dict, description="Individual metric scores"
    )
    overall_score: float = Field(
        default=0.0, ge=0.0, le=1.0, description="Overall weighted score"
    )

    # Metadata
    latency_ms: Optional[float] = Field(default=None, description="Latency in milliseconds")
    error: Optional[str] = Field(default=None, description="Error message if failed")
    metadata: Dict[str, Any] = Field(
        default_factory=dict, description="Additional metadata"
    )
