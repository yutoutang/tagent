"""
YAML configuration loader.

Following intent_system/workflow/json_loader.py pattern.
"""

import os
from pathlib import Path
from typing import Union

import yaml

from .models import EvaluationConfig


class ConfigLoader:
    """
    Configuration loader for YAML files.

    Features:
    - YAML file loading
    - Environment variable substitution
    - Configuration validation
    """

    @staticmethod
    def load_from_file(
        config_path: Union[str, Path], substitute_env: bool = True
    ) -> EvaluationConfig:
        """
        Load configuration from YAML file.

        Args:
            config_path: Path to YAML configuration file
            substitute_env: Whether to substitute environment variables

        Returns:
            EvaluationConfig instance

        Raises:
            FileNotFoundError: If config file doesn't exist
            ValueError: If YAML format is invalid
        """
        path = Path(config_path)
        if not path.exists():
            raise FileNotFoundError(f"Configuration file not found: {config_path}")

        # Read YAML file
        with open(path, "r", encoding="utf-8") as f:
            config_data = yaml.safe_load(f)

        # Substitute environment variables if enabled
        if substitute_env:
            config_data = ConfigLoader._substitute_env_vars(config_data)

        # Validate and create EvaluationConfig
        try:
            return EvaluationConfig(**config_data)
        except Exception as e:
            raise ValueError(f"Invalid configuration format: {e}")

    @staticmethod
    def _substitute_env_vars(data: dict) -> dict:
        """
        Recursively substitute environment variables in configuration.

        Supports syntax: ${ENV_VAR} or $ENV_VAR

        Args:
            data: Configuration dictionary

        Returns:
            Dictionary with substituted values
        """
        result = {}

        for key, value in data.items():
            if isinstance(value, dict):
                result[key] = ConfigLoader._substitute_env_vars(value)
            elif isinstance(value, str):
                # Check for ${VAR} or $VAR syntax
                if value.startswith("${") and value.endswith("}"):
                    env_var = value[2:-1]
                    env_value = os.getenv(env_var)
                    result[key] = env_value if env_value is not None else value
                elif value.startswith("$") and not value.startswith("${"):
                    env_var = value[1:]
                    env_value = os.getenv(env_var)
                    result[key] = env_value if env_value is not None else value
                else:
                    result[key] = value
            else:
                result[key] = value

        return result

    @staticmethod
    def load_from_dict(config_data: dict) -> EvaluationConfig:
        """
        Load configuration from dictionary.

        Args:
            config_data: Configuration dictionary

        Returns:
            EvaluationConfig instance
        """
        return EvaluationConfig(**config_data)

    @staticmethod
    def save_to_file(config: EvaluationConfig, output_path: Union[str, Path]) -> None:
        """
        Save configuration to YAML file.

        Args:
            config: EvaluationConfig instance
            output_path: Output file path
        """
        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)

        with open(path, "w", encoding="utf-8") as f:
            yaml.dump(
                config.model_dump(exclude_none=True),
                f,
                default_flow_style=False,
                allow_unicode=True,
                sort_keys=False,
            )
