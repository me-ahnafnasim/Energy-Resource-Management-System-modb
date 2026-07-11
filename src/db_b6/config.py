from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Optional

from dotenv import load_dotenv


load_dotenv()


def _bool_env(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "y", "on"}


def _int_env(name: str, default: int) -> int:
    value = os.getenv(name)
    if not value:
        return default
    return int(value)


def _optional_env(name: str) -> Optional[str]:
    value = os.getenv(name)
    if value is None:
        return None
    value = value.strip()
    return value or None


@dataclass(frozen=True)
class MqttConfig:
    host: str
    port: int
    username: Optional[str]
    password: Optional[str]
    use_tls: bool
    keepalive: int
    publish_interval_seconds: int
    sample_interval_seconds: int
    topic_prefix: str


@dataclass(frozen=True)
class MongoConfig:
    uri: str
    database: str
    collection: str


@dataclass(frozen=True)
class PostgresConfig:
    dsn: Optional[str]
    host: Optional[str]
    port: int
    database: Optional[str]
    user: Optional[str]
    password: Optional[str]
    sslmode: str


@dataclass(frozen=True)
class Neo4jConfig:
    uri: str
    username: str
    password: str
    database: str


@dataclass(frozen=True)
class Settings:
    mqtt: MqttConfig
    mongo: MongoConfig
    postgres: PostgresConfig
    neo4j: Neo4jConfig


def get_settings() -> Settings:
    return Settings(
        mqtt=MqttConfig(
            host=os.getenv("MQTT_HOST", "localhost"),
            port=_int_env("MQTT_PORT", 1883),
            username=_optional_env("MQTT_USERNAME"),
            password=_optional_env("MQTT_PASSWORD"),
            use_tls=_bool_env("MQTT_USE_TLS", False),
            keepalive=_int_env("MQTT_KEEPALIVE", 60),
            publish_interval_seconds=_int_env("MQTT_PUBLISH_INTERVAL_SECONDS", 5),
            sample_interval_seconds=_int_env("ENERGY_SAMPLE_INTERVAL_SECONDS", 5),
            topic_prefix=os.getenv("MQTT_TOPIC_PREFIX", "energy").strip().strip("/") or "energy",
        ),
        mongo=MongoConfig(
            uri=os.getenv("MONGO_URI", ""),
            database=os.getenv("MONGO_DB", "energy_monitoring"),
            collection=os.getenv("MONGO_COLLECTION", "energy_readings"),
        ),
        postgres=PostgresConfig(
            dsn=_optional_env("POSTGRES_DSN"),
            host=_optional_env("POSTGRES_HOST"),
            port=_int_env("POSTGRES_PORT", 5432),
            database=_optional_env("POSTGRES_DB"),
            user=_optional_env("POSTGRES_USER"),
            password=_optional_env("POSTGRES_PASSWORD"),
            sslmode=os.getenv("POSTGRES_SSLMODE", "require"),
        ),
        neo4j=Neo4jConfig(
            uri=os.getenv("NEO4J_URI", ""),
            username=os.getenv("NEO4J_USERNAME", "neo4j"),
            password=os.getenv("NEO4J_PASSWORD", ""),
            database=os.getenv("NEO4J_DATABASE", "neo4j"),
        ),
    )
