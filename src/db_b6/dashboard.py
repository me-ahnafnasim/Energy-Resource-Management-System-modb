from __future__ import annotations

import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd
import streamlit as st
from neo4j import GraphDatabase
from pymongo import DESCENDING, MongoClient

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.db_b6.config import get_settings
from src.db_b6.database import postgres_connection


RECENT_LIMIT = 100


def flatten_reading(reading: dict[str, Any]) -> dict[str, Any]:
    metrics = reading.get("metrics") or {}
    environment = reading.get("environment") or {}

    return {
        "timestamp": reading.get("timestamp"),
        "device_id": reading.get("device_id"),
        "power_watts": metrics.get("power_watts"),
        "voltage": metrics.get("voltage"),
        "current_amp": metrics.get("current_amp"),
        "temperature_c": environment.get("temperature_c"),
        "humidity_pct": environment.get("humidity_pct"),
        "status": reading.get("status"),
        "topic": reading.get("topic"),
        "ingested_at": reading.get("ingested_at"),
    }


def load_mongo_data() -> tuple[int, pd.DataFrame]:
    settings = get_settings()
    client = MongoClient(settings.mongo.uri)
    try:
        collection = client[settings.mongo.database][settings.mongo.collection]
        total_readings = collection.count_documents({})
        readings = list(
            collection.find({}, {"_id": 0})
            .sort("timestamp", DESCENDING)
            .limit(RECENT_LIMIT)
        )
    finally:
        client.close()

    rows = [flatten_reading(reading) for reading in readings]
    frame = pd.DataFrame(rows)
    if not frame.empty:
        frame["timestamp"] = pd.to_datetime(frame["timestamp"], errors="coerce")
        frame = frame.sort_values("timestamp", ascending=False)
    return total_readings, frame


def load_postgres_data() -> tuple[pd.DataFrame, dict[str, int]]:
    settings = get_settings()
    with postgres_connection(settings.postgres) as conn:
        counts: dict[str, int] = {}
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT
                    date,
                    device_id,
                    ROUND(total_kwh::numeric, 6) AS total_kwh,
                    ROUND(avg_power::numeric, 2) AS avg_power,
                    reading_count,
                    last_updated
                FROM daily_summary
                ORDER BY last_updated DESC, device_id;
                """
            )
            columns = [description[0] for description in cur.description]
            summary = pd.DataFrame(cur.fetchall(), columns=columns)

            for table in ("buildings", "rooms", "devices", "daily_summary"):
                cur.execute(f"SELECT COUNT(*) FROM {table}")
                counts[table] = int(cur.fetchone()[0])
            cur.execute("SELECT COALESCE(SUM(reading_count), 0) FROM daily_summary")
            counts["aggregated_readings"] = int(cur.fetchone()[0])

    return summary, counts


def load_neo4j_data() -> tuple[pd.DataFrame, int]:
    settings = get_settings()
    driver = GraphDatabase.driver(
        settings.neo4j.uri,
        auth=(settings.neo4j.username, settings.neo4j.password),
    )
    try:
        with driver.session(database=settings.neo4j.database) as session:
            node_count = session.run("MATCH (n) RETURN count(n) AS count").single()["count"]
            records = session.run(
                """
                MATCH (b:Building)-[:CONTAINS]->(r:Room)-[:HAS_DEVICE]->(d:Device)
                RETURN
                    b.id AS building_id,
                    b.name AS building_name,
                    r.id AS room_id,
                    r.room_number AS room_number,
                    d.id AS device_id,
                    d.type AS device_type
                ORDER BY building_id, room_id, device_id;
                """
            )
            rows = [dict(record) for record in records]
    finally:
        driver.close()

    return pd.DataFrame(rows), int(node_count)


def render_error(source: str, exc: Exception) -> None:
    st.error(f"{source} error: {exc}")


def main() -> None:
    settings = get_settings()

    st.set_page_config(
        page_title="DB-B6 Energy Dashboard",
        layout="wide",
    )

    st.title("DB-B6 Energy Dashboard")
    top_left, top_right = st.columns([4, 1])
    with top_left:
        st.caption(
            f"MQTT topic: `{settings.mqtt.topic_prefix}/#` | "
            f"Loaded at: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}"
        )
    with top_right:
        if st.button("Refresh Data", use_container_width=True):
            st.rerun()

    mongo_count = 0
    mongo_frame = pd.DataFrame()
    summary_frame = pd.DataFrame()
    postgres_counts = {
        "buildings": 0,
        "rooms": 0,
        "devices": 0,
        "daily_summary": 0,
        "aggregated_readings": 0,
    }
    graph_frame = pd.DataFrame()
    neo4j_nodes = 0

    try:
        mongo_count, mongo_frame = load_mongo_data()
    except Exception as exc:
        render_error("MongoDB", exc)

    try:
        summary_frame, postgres_counts = load_postgres_data()
    except Exception as exc:
        render_error("PostgreSQL", exc)

    try:
        graph_frame, neo4j_nodes = load_neo4j_data()
    except Exception as exc:
        render_error("Neo4j", exc)

    metric_cols = st.columns(4)
    metric_cols[0].metric("MongoDB Readings", f"{mongo_count:,}")
    metric_cols[1].metric("Registered Devices", f"{postgres_counts['devices']:,}")
    metric_cols[2].metric("Aggregated Readings", f"{postgres_counts['aggregated_readings']:,}")
    metric_cols[3].metric("Neo4j Nodes", f"{neo4j_nodes:,}")

    st.divider()

    left_col, right_col = st.columns([1.35, 1])

    with left_col:
        st.subheader("Latest Raw Readings")
        if mongo_frame.empty:
            st.info("No MongoDB readings found yet.")
        else:
            visible_columns = [
                "timestamp",
                "device_id",
                "power_watts",
                "voltage",
                "current_amp",
                "temperature_c",
                "humidity_pct",
                "status",
            ]
            st.dataframe(
                mongo_frame[visible_columns],
                use_container_width=True,
                hide_index=True,
            )

    with right_col:
        st.subheader("Recent Power")
        if mongo_frame.empty:
            st.info("No chart data found yet.")
        else:
            chart_frame = mongo_frame[["timestamp", "device_id", "power_watts"]].dropna()
            chart_frame = chart_frame.sort_values("timestamp")
            if chart_frame.empty:
                st.info("No power readings found yet.")
            else:
                pivot = chart_frame.pivot_table(
                    index="timestamp",
                    columns="device_id",
                    values="power_watts",
                    aggfunc="mean",
                )
                st.line_chart(pivot, use_container_width=True)

    st.divider()

    summary_col, graph_col = st.columns(2)

    with summary_col:
        st.subheader("PostgreSQL Daily Summary")
        st.caption(
            f"Buildings: {postgres_counts['buildings']} | "
            f"Rooms: {postgres_counts['rooms']} | "
            f"Summary rows: {postgres_counts['daily_summary']}"
        )
        if summary_frame.empty:
            st.info("No PostgreSQL summary data found yet.")
        else:
            st.dataframe(summary_frame, use_container_width=True, hide_index=True)

    with graph_col:
        st.subheader("Neo4j Relationships")
        if graph_frame.empty:
            st.info("No Neo4j relationship data found yet.")
        else:
            st.dataframe(graph_frame, use_container_width=True, hide_index=True)


if __name__ == "__main__":
    main()
