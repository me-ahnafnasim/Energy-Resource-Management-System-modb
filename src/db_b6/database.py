from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime, timezone
from typing import Any, Iterator

import psycopg2
from neo4j import GraphDatabase
from pymongo import ASCENDING, MongoClient

from .config import MongoConfig, Neo4jConfig, PostgresConfig
from .devices import BUILDINGS, DEVICES, ROOMS


def require_value(value: str | None, name: str) -> str:
    if not value:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value


@contextmanager
def postgres_connection(config: PostgresConfig) -> Iterator[Any]:
    if config.dsn:
        conn = psycopg2.connect(config.dsn)
    else:
        conn = psycopg2.connect(
            host=require_value(config.host, "POSTGRES_HOST"),
            port=config.port,
            dbname=require_value(config.database, "POSTGRES_DB"),
            user=require_value(config.user, "POSTGRES_USER"),
            password=require_value(config.password, "POSTGRES_PASSWORD"),
            sslmode=config.sslmode,
        )

    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_postgres(config: PostgresConfig) -> None:
    with postgres_connection(config) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS buildings (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    location TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS rooms (
                    id TEXT PRIMARY KEY,
                    building_id TEXT NOT NULL REFERENCES buildings(id),
                    room_number TEXT NOT NULL,
                    floor INTEGER NOT NULL
                );

                CREATE TABLE IF NOT EXISTS devices (
                    id TEXT PRIMARY KEY,
                    room_id TEXT NOT NULL REFERENCES rooms(id),
                    type TEXT NOT NULL,
                    install_date DATE NOT NULL
                );

                CREATE TABLE IF NOT EXISTS daily_summary (
                    date DATE NOT NULL,
                    device_id TEXT NOT NULL REFERENCES devices(id),
                    total_kwh DOUBLE PRECISION NOT NULL DEFAULT 0,
                    avg_power DOUBLE PRECISION NOT NULL DEFAULT 0,
                    reading_count INTEGER NOT NULL DEFAULT 0,
                    last_updated TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    PRIMARY KEY (date, device_id)
                );
                """
            )

            cur.executemany(
                """
                INSERT INTO buildings (id, name, location)
                VALUES (%s, %s, %s)
                ON CONFLICT (id) DO UPDATE
                SET name = EXCLUDED.name,
                    location = EXCLUDED.location;
                """,
                [(b.id, b.name, b.location) for b in BUILDINGS],
            )
            cur.executemany(
                """
                INSERT INTO rooms (id, building_id, room_number, floor)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT (id) DO UPDATE
                SET building_id = EXCLUDED.building_id,
                    room_number = EXCLUDED.room_number,
                    floor = EXCLUDED.floor;
                """,
                [(r.id, r.building_id, r.room_number, r.floor) for r in ROOMS],
            )
            cur.executemany(
                """
                INSERT INTO devices (id, room_id, type, install_date)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT (id) DO UPDATE
                SET room_id = EXCLUDED.room_id,
                    type = EXCLUDED.type,
                    install_date = EXCLUDED.install_date;
                """,
                [(d.id, d.room_id, d.type, d.install_date) for d in DEVICES],
            )


def update_daily_summary(
    config: PostgresConfig,
    device_id: str,
    timestamp: datetime,
    power_watts: float,
    sample_interval_seconds: int,
) -> None:
    reading_date = timestamp.date()
    kwh = power_watts * sample_interval_seconds / 3_600_000

    with postgres_connection(config) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO daily_summary
                    (date, device_id, total_kwh, avg_power, reading_count, last_updated)
                VALUES (%s, %s, %s, %s, 1, NOW())
                ON CONFLICT (date, device_id) DO UPDATE
                SET total_kwh = daily_summary.total_kwh + EXCLUDED.total_kwh,
                    avg_power = (
                        (daily_summary.avg_power * daily_summary.reading_count)
                        + EXCLUDED.avg_power
                    ) / (daily_summary.reading_count + 1),
                    reading_count = daily_summary.reading_count + 1,
                    last_updated = NOW();
                """,
                (reading_date, device_id, kwh, power_watts),
            )


def init_mongo(config: MongoConfig) -> None:
    client = MongoClient(require_value(config.uri, "MONGO_URI"))
    try:
        collection = client[config.database][config.collection]
        collection.create_index(
            [("device_id", ASCENDING), ("timestamp", ASCENDING)],
            name="device_timestamp_idx",
        )
    finally:
        client.close()


def insert_mongo_reading(config: MongoConfig, reading: dict[str, Any]) -> None:
    client = MongoClient(require_value(config.uri, "MONGO_URI"))
    try:
        collection = client[config.database][config.collection]
        collection.insert_one(reading)
    finally:
        client.close()


def init_neo4j(config: Neo4jConfig) -> None:
    driver = GraphDatabase.driver(
        require_value(config.uri, "NEO4J_URI"),
        auth=(config.username, require_value(config.password, "NEO4J_PASSWORD")),
    )
    try:
        with driver.session(database=config.database) as session:
            session.execute_write(_create_graph_constraints)
            session.execute_write(_create_graph_metadata)
    finally:
        driver.close()


def _create_graph_constraints(tx: Any) -> None:
    tx.run("CREATE CONSTRAINT building_id IF NOT EXISTS FOR (b:Building) REQUIRE b.id IS UNIQUE")
    tx.run("CREATE CONSTRAINT room_id IF NOT EXISTS FOR (r:Room) REQUIRE r.id IS UNIQUE")
    tx.run("CREATE CONSTRAINT device_id IF NOT EXISTS FOR (d:Device) REQUIRE d.id IS UNIQUE")


def _create_graph_metadata(tx: Any) -> None:
    for building in BUILDINGS:
        tx.run(
            """
            MERGE (b:Building {id: $id})
            SET b.name = $name,
                b.location = $location
            """,
            id=building.id,
            name=building.name,
            location=building.location,
        )

    for room in ROOMS:
        tx.run(
            """
            MATCH (b:Building {id: $building_id})
            MERGE (r:Room {id: $id})
            SET r.room_number = $room_number,
                r.floor = $floor
            MERGE (b)-[:CONTAINS]->(r)
            """,
            id=room.id,
            building_id=room.building_id,
            room_number=room.room_number,
            floor=room.floor,
        )

    for device in DEVICES:
        tx.run(
            """
            MATCH (r:Room {id: $room_id})
            MERGE (d:Device {id: $id})
            SET d.type = $type,
                d.install_date = date($install_date)
            MERGE (r)-[:HAS_DEVICE]->(d)
            """,
            id=device.id,
            room_id=device.room_id,
            type=device.type,
            install_date=device.install_date,
        )


def parse_iso_timestamp(value: str) -> datetime:
    normalized = value.replace("Z", "+00:00")
    parsed = datetime.fromisoformat(normalized)
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)
