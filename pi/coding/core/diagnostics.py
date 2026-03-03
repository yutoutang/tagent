"""Resource loading diagnostics for pi-coding.

Converted from TypeScript core/diagnostics.ts
"""
from dataclasses import dataclass, field
from typing import Literal, Optional


@dataclass
class ResourceCollision:
    """Information about a resource name collision."""
    resource_type: Literal["extension", "skill", "prompt", "theme"]
    name: str
    winner_path: str
    loser_path: str
    winner_source: Optional[str] = None
    loser_source: Optional[str] = None


@dataclass
class ResourceDiagnostic:
    """A diagnostic message from resource loading."""
    type: Literal["warning", "error", "collision"]
    message: str
    path: Optional[str] = None
    collision: Optional[ResourceCollision] = field(default=None, repr=False)


__all__ = [
    "ResourceCollision",
    "ResourceDiagnostic",
]
