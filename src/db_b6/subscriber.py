from __future__ import annotations

import json
import ssl
from datetime import datetime, timezone
from typing import Any

import paho.mqtt.client as mqtt

from .config import MqttConfig, get_settings
from .database import insert_mongo_reading, parse_iso_timestamp, update_daily_summary


def build_client(config: MqttConfig) -> mqtt.Client:
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id="db-b6-subscriber")

    if config.username:
        client.username_pw_set(config.username, config.password)

    if config.use_tls:
        client.tls_set(cert_reqs=ssl.CERT_REQUIRED)

    return client


def process_message(topic: str, payload: bytes) -> None:
    settings = get_settings()
    message: dict[str, Any] = json.loads(payload.decode("utf-8"))
    timestamp = parse_iso_timestamp(message["timestamp"])
    power_watts = float(message["metrics"]["power_watts"])

    reading = {
        **message,
        "topic": topic,
        "topic_parts": topic.split("/"),
        "ingested_at": datetime.now(timezone.utc),
    }

    insert_mongo_reading(settings.mongo, reading)
    update_daily_summary(
        settings.postgres,
        device_id=message["device_id"],
        timestamp=timestamp,
        power_watts=power_watts,
        sample_interval_seconds=settings.mqtt.sample_interval_seconds,
    )


def main() -> None:
    settings = get_settings()
    client = build_client(settings.mqtt)

    def on_connect(client: mqtt.Client, userdata: Any, flags: Any, reason_code: Any, properties: Any) -> None:
        if reason_code == 0:
            topic_filter = f"{settings.mqtt.topic_prefix}/#"
            client.subscribe(topic_filter, qos=1)
            print(f"Subscriber connected and listening on {topic_filter}")
        else:
            print(f"Subscriber connection failed: {reason_code}")

    def on_message(client: mqtt.Client, userdata: Any, msg: mqtt.MQTTMessage) -> None:
        try:
            process_message(msg.topic, msg.payload)
            print(f"Processed reading from {msg.topic}")
        except Exception as exc:
            print(f"Failed to process message from {msg.topic}: {exc}")

    client.on_connect = on_connect
    client.on_message = on_message

    client.connect(settings.mqtt.host, settings.mqtt.port, settings.mqtt.keepalive)

    try:
        client.loop_forever()
    except KeyboardInterrupt:
        print("Subscriber stopped.")
    finally:
        client.disconnect()


if __name__ == "__main__":
    main()
