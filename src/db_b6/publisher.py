from __future__ import annotations

import json
import random
import ssl
import time
from datetime import datetime, timezone

import paho.mqtt.client as mqtt

from .config import MqttConfig, get_settings
from .devices import DEVICES, Device


def build_client(config: MqttConfig) -> mqtt.Client:
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id="db-b6-publisher")

    if config.username:
        client.username_pw_set(config.username, config.password)

    if config.use_tls:
        client.tls_set(cert_reqs=ssl.CERT_REQUIRED)

    return client


def generate_reading(device: Device) -> dict:
    now = datetime.now(timezone.utc)
    hour = now.hour
    day_multiplier = 1.25 if 8 <= hour <= 18 else 0.55

    if device.type == "hvac":
        variation = random.uniform(0.55, 1.35)
    elif device.type == "lighting":
        variation = random.uniform(0.35, 1.1)
    elif device.type == "plug_load":
        variation = random.uniform(0.25, 1.2)
    else:
        variation = random.uniform(0.7, 1.15)

    power_watts = round(device.nominal_power_watts * day_multiplier * variation, 2)
    voltage = round(random.uniform(216.0, 244.0), 1)
    current_amp = round(power_watts / voltage, 2)

    return {
        "device_id": device.id,
        "timestamp": now.isoformat().replace("+00:00", "Z"),
        "metrics": {
            "power_watts": power_watts,
            "voltage": voltage,
            "current_amp": current_amp,
        },
        "environment": {
            "temperature_c": round(random.uniform(19.0, 28.0), 1),
            "humidity_pct": round(random.uniform(35.0, 62.0), 1),
        },
        "status": "active" if random.random() > 0.02 else "maintenance",
    }


def topic_for_device(topic_prefix: str, device: Device) -> str:
    return f"{topic_prefix}/{device.building_id}/{device.room_id}/{device.type}/data"


def main() -> None:
    settings = get_settings()
    client = build_client(settings.mqtt)
    client.connect(settings.mqtt.host, settings.mqtt.port, settings.mqtt.keepalive)
    client.loop_start()

    print(f"Publishing {len(DEVICES)} devices to MQTT broker {settings.mqtt.host}:{settings.mqtt.port}")
    try:
        while True:
            for device in DEVICES:
                payload = generate_reading(device)
                message = json.dumps(payload)
                topic = topic_for_device(settings.mqtt.topic_prefix, device)
                result = client.publish(topic, message, qos=1)
                result.wait_for_publish()
                print(f"Published {payload['device_id']} -> {topic}: {message}")

            time.sleep(settings.mqtt.publish_interval_seconds)
    except KeyboardInterrupt:
        print("Publisher stopped.")
    finally:
        client.loop_stop()
        client.disconnect()


if __name__ == "__main__":
    main()
