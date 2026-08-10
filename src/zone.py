from enum import Enum

from pydantic import BaseModel, ConfigDict, Field


class ZoneType(Enum):
    """Possible types for a zone."""

    NORMAL = "normal"
    BLOCKED = "blocked"
    RESTRICTED = "restricted"
    PRIORITY = "priority"

    def movement_cost(self) -> int:
        """Return the turn cost to move INTO this zone type."""
        if self == ZoneType.RESTRICTED:
            return 2
        return 1  # normal and priority both cost 1 turn


class Zone(BaseModel):
    """Represents a single zone (node) in the drone network."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    name: str = Field(min_length=1)
    x: int
    y: int
    zone_type: ZoneType = ZoneType.NORMAL
    color: str = "none"
    max_drones: int = Field(default=1, ge=1)
    is_start: bool = False
    is_end: bool = False

    def __repr__(self) -> str:
        """Return readable string for debugging."""
        return (
            f"Zone(name={self.name!r}, type={self.zone_type.value}, "
            f"pos=({self.x},{self.y}), max={self.max_drones})"
        )
