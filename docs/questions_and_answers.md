# Project Questions and Short Answers

## 1. Explain how this project works.

This project simulates IoT energy sensors using Python. The publisher script generates fake energy readings and sends them through MQTT. The subscriber receives those messages and stores the data in three cloud databases.

## 2. What is the data source?

The data source is `publisher.py`. It simulates sensor devices by generating random values for power, voltage, current, temperature, and humidity.

## 3. Why did you use MQTT?

MQTT is commonly used in IoT systems because it is lightweight and works well for sending sensor data from devices to a central application.

## 4. What does the subscriber do?

The subscriber listens to MQTT topics, receives JSON sensor messages, and sends the data to the correct databases.

## 5. What data is stored in MongoDB?

MongoDB stores raw sensor readings. Each reading includes device ID, timestamp, power, voltage, current, temperature, humidity, status, and MQTT topic.

## 6. Why did you use MongoDB?

MongoDB is good for raw IoT data because the sensor message is already in JSON format and can be stored as a document.

## 7. What data is stored in PostgreSQL?

PostgreSQL stores structured data such as buildings, rooms, devices, and daily energy summaries.

## 8. Why did you use PostgreSQL?

PostgreSQL is good for structured data because it supports tables, relationships, constraints, and SQL queries.

## 9. What data is stored in Neo4j?

Neo4j stores relationships between buildings, rooms, and devices. For example, a building contains rooms, and each room has devices.

## 10. Why did you use Neo4j?

Neo4j is good for graph data because it clearly shows relationships like `Building -> Room -> Device`.

## 11. What is the MQTT topic format?

The topic format is:

```text
energy/db_b6_4b061187/{building_id}/{room_id}/{device_type}/data
```

Example:

```text
energy/db_b6_4b061187/building_A/room_101/smart_meter/data
```

## 12. What happens when the publisher runs?

The publisher sends simulated sensor readings every few seconds to the MQTT broker.

## 13. What happens when the subscriber runs?

The subscriber receives MQTT messages, inserts raw data into MongoDB, and updates daily summaries in PostgreSQL.

## 14. Does Neo4j receive every sensor reading?

No. Neo4j stores the system structure and relationships, not every live reading.

## 15. How can you prove the system is working?

Run the subscriber and publisher together. Then check MongoDB for new raw readings, PostgreSQL for updated `daily_summary`, and Neo4j for the building-room-device graph.

## 16. What are the main Python files?

`publisher.py` sends simulated sensor data. `subscriber.py` receives and stores the data. `init_db.py` creates the database tables, indexes, and graph relationships.

## 17. Why use three databases instead of one?

Each database is used for what it does best. MongoDB stores raw JSON readings, PostgreSQL stores structured summaries, and Neo4j stores relationships.

## 18. What is one challenge in this project?

One challenge is connecting different cloud databases and making sure data is sent to the correct place.

