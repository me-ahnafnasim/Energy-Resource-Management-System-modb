from __future__ import annotations

from .config import get_settings
from .database import init_mongo, init_neo4j, init_postgres


def main() -> None:
    settings = get_settings()

    print("Initializing PostgreSQL tables and seed metadata...")
    init_postgres(settings.postgres)

    print("Initializing MongoDB collection and indexes...")
    init_mongo(settings.mongo)

    print("Initializing Neo4j graph metadata...")
    init_neo4j(settings.neo4j)

    print("Database initialization complete.")


if __name__ == "__main__":
    main()

