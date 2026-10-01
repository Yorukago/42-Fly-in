from dataclasses import dataclass, field
from enum import Enum


class EventKind(Enum):
    """What a drone did on one turn."""

    WAIT = "wait"
    ARRIVE = "arrive"
    TRANSIT = "transit"


@dataclass(frozen=True)
class DroneEvent:
    """A single turn's outcome for one drone."""

    turn: int
    kind: EventKind
    zone: str
    connection_key: frozenset[str] | None = None


@dataclass
class Drone:
    """One drone, and the turn-by-turn events that make up its route."""

    drone_id: int
    events: list[DroneEvent] = field(default_factory=list)

    @property
    def label(self) -> str:
        """Return the drone's display label, "D<id>"."""
        return f"D{self.drone_id}"

    @property
    def arrival_turn(self) -> int:
        """Return the turn the drone reaches its destination, 0 if unplanned."""
        return self.events[-1].turn if self.events else 0
