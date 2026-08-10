from pydantic import BaseModel, ConfigDict, Field, model_validator


class Connection(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    zone_a: str = Field(min_length=1)
    zone_b: str = Field(min_length=1)
    max_link_capacity: int = Field(default=1, ge=1)

    @model_validator(mode="after")
    def _check_not_self_loop(self) -> "Connection":
        if self.zone_a == self.zone_b:
            raise ValueError(f"a connection cannot link a zone to itself: {self.zone_a!r}")
        return self

    def connects(self, name: str) -> bool:
        return name == self.zone_a or name == self.zone_b

    def other(self, name: str) -> str:
        if name == self.zone_a:
            return self.zone_b
        return self.zone_a

    def __repr__(self) -> str:
        return (
            f"Connection({self.zone_a!r} <-> {self.zone_b!r}, "
            f"capacity={self.max_link_capacity})"
        )
