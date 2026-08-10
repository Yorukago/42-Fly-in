from dataclasses import dataclass, field
from enum import Enum


class EventKind(Enum):
    """Possible kinds of per-turn drone events."""

    WAIT = "wait"  # stayed in the same zone this turn
    # arrived at a zone: a normal/priority move, or the 2nd turn of a restricted move
    ARRIVE = "arrive"
    TRANSIT = "transit"  # 1st turn of a 2-turn restricted move (still in flight)


@dataclass(frozen=True)
class DroneEvent:
    """A single turn's outcome for one drone."""

    turn: int
    kind: EventKind
    zone: str
    connection_key: frozenset[str] | None = None


@dataclass
class DronePlan:
    """The finalized, turn-by-turn plan for a single drone."""

    events: list[DroneEvent] = field(default_factory=list)

    @property
    def arrival_turn(self) -> int:
        """Return the turn on which the drone reaches its destination.

        Returns:
            The turn number of the last recorded event, or 0 if empty.
        """
        return self.events[-1].turn if self.events else 0


class Drone:
    """A single drone, identified by a numeric id."""

    def __init__(self, drone_id: int) -> None:
        """Initialize a drone with the given id.

        Args:
            drone_id: The drone's unique numeric identifier.
        """
        self.drone_id = drone_id
        self.plan = DronePlan()

    @property
    def label(self) -> str:
        """Return the drone's display label.

        Returns:
            A string of the form "D<id>".
        """
        return f"D{self.drone_id}"

    def __repr__(self) -> str:
        """Return a readable string for debugging."""
        return f"Drone({self.label}, arrival_turn={self.plan.arrival_turn})"
