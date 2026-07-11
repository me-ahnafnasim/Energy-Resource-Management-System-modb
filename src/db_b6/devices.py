from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable


@dataclass(frozen=True)
class Building:
    id: str
    name: str
    location: str


@dataclass(frozen=True)
class Room:
    id: str
    building_id: str
    room_number: str
    floor: int


@dataclass(frozen=True)
class Device:
    id: str
    room_id: str
    building_id: str
    room_number: str
    type: str
    install_date: str
    nominal_power_watts: float

    @property
    def topic(self) -> str:
        return f"energy/{self.building_id}/{self.room_id}/{self.type}/data"


BUILDINGS: tuple[Building, ...] = (
    Building("building_A", "Engineering Building A", "Main Campus"),
    Building("building_B", "Library Building B", "North Campus"),
)

ROOMS: tuple[Room, ...] = (
    Room("room_101", "building_A", "101", 1),
    Room("room_102", "building_A", "102", 1),
    Room("room_201", "building_A", "201", 2),
    Room("room_301", "building_B", "301", 3),
    Room("room_302", "building_B", "302", 3),
)

DEVICES: tuple[Device, ...] = (
    Device("sm_001", "room_101", "building_A", "101", "smart_meter", "2026-01-12", 420.0),
    Device("hvac_001", "room_101", "building_A", "101", "hvac", "2026-01-15", 1650.0),
    Device("light_001", "room_102", "building_A", "102", "lighting", "2026-02-02", 180.0),
    Device("plug_001", "room_102", "building_A", "102", "plug_load", "2026-02-03", 260.0),
    Device("sm_002", "room_201", "building_A", "201", "smart_meter", "2026-02-08", 510.0),
    Device("hvac_002", "room_201", "building_A", "201", "hvac", "2026-02-08", 1900.0),
    Device("light_002", "room_301", "building_B", "301", "lighting", "2026-03-01", 220.0),
    Device("plug_002", "room_301", "building_B", "301", "plug_load", "2026-03-01", 320.0),
    Device("sm_003", "room_302", "building_B", "302", "smart_meter", "2026-03-05", 470.0),
    Device("hvac_003", "room_302", "building_B", "302", "hvac", "2026-03-05", 1750.0),
)


def all_metadata() -> tuple[Iterable[Building], Iterable[Room], Iterable[Device]]:
    return BUILDINGS, ROOMS, DEVICES

