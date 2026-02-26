"""
Dataset loader.

Following intent_system/workflow/json_loader.py pattern.
"""

import json
from pathlib import Path
from typing import Union

from .models import Dataset, DatasetItem


class DatasetLoader:
    """
    Dataset loader for JSON files.
    """

    @staticmethod
    def load_from_file(file_path: Union[str, Path]) -> Dataset:
        """
        Load dataset from JSON file.

        Args:
            file_path: Path to dataset file

        Returns:
            Dataset instance

        Raises:
            FileNotFoundError: If file doesn't exist
            ValueError: If format is invalid
        """
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"Dataset file not found: {file_path}")

        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)

        # Parse dataset items
        items = []
        for item_data in data.get("items", []):
            item = DatasetItem(
                input=item_data.get("input"),
                expected=item_data.get("expected"),
                metadata=item_data.get("metadata", {}),
            )
            items.append(item)

        return Dataset(
            name=data.get("name", "unnamed"),
            description=data.get("description"),
            items=items,
        )

    @staticmethod
    def save_to_file(dataset: Dataset, output_path: Union[str, Path]) -> None:
        """
        Save dataset to JSON file.

        Args:
            dataset: Dataset instance
            output_path: Output file path
        """
        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)

        data = {
            "name": dataset.name,
            "description": dataset.description,
            "items": [
                {"input": item.input, "expected": item.expected, "metadata": item.metadata}
                for item in dataset.items
            ],
        }

        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
