"""
Dataset models.

Following intent_system/workflow/workflow_intent.py pattern.
"""

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class DatasetItem(BaseModel):
    """
    Single dataset item.
    """

    input: Any = Field(description="Input data")
    expected: Optional[Any] = Field(default=None, description="Expected output")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")


class Dataset(BaseModel):
    """
    Evaluation dataset.
    """

    name: str = Field(description="Dataset name")
    description: Optional[str] = Field(default=None, description="Dataset description")
    items: List[DatasetItem] = Field(description="Dataset items")

    def __len__(self) -> int:
        return len(self.items)

    def __getitem__(self, index: int) -> DatasetItem:
        return self.items[index]
