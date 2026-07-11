# DB-B6 Energy Resource Management Report

## 1. Introduction

This project simulates an IoT energy monitoring system. Python sensor publishers send energy readings through MQTT, and a Python subscriber processes the messages into three cloud database platforms.

## 2. System Architecture

Data flow:

```text
Python Sensor Simulator -> MQTT Broker -> Python Subscriber
                                      -> MongoDB Atlas
                                      -> PostgreSQL Cloud Database
                                      -> Neo4j Aura
```

## 3. Cloud Database Choices

MongoDB Atlas stores raw sensor readings because the JSON payload is flexible and naturally document-shaped.

PostgreSQL stores structured metadata and daily summaries because buildings, rooms, devices, and aggregates benefit from relational constraints.

Neo4j Aura stores relationships because the building-room-device structure is easy to query and visualize as a graph.

## 4. Implementation

Main files:

- `src/db_b6/init_db.py`: creates tables, indexes, seed data, and graph relationships
- `src/db_b6/publisher.py`: simulates energy devices and publishes MQTT JSON messages
- `src/db_b6/subscriber.py`: subscribes to `energy/#`, inserts raw data, and updates aggregates

## 5. Screenshots

Add screenshots for:

- MQTT broker or HiveMQ dashboard
- MongoDB Atlas collection documents
- PostgreSQL tables and `daily_summary`
- Neo4j graph visualization

## 6. Challenges

Discuss connection strings, environment variables, cloud database SSL, and how MQTT messages are processed asynchronously.

## 7. Conclusion

The system demonstrates how different cloud database models can be combined in one IoT application: document storage for raw events, relational storage for summaries, and graph storage for relationships.

