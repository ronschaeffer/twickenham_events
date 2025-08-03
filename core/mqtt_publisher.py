import json
import ssl
import time
from typing import Any

import paho.mqtt.client as mqtt


class MQTTPublisher:
    def __init__(
        self,
        broker_url: str,
        broker_port: int,
        client_id: str,
        security: str = "none",
        auth: dict | None = None,
        tls: dict | None = None,
        max_retries: int = 3,
    ):
        self.client = mqtt.Client(client_id=client_id)
        self.broker_url = broker_url
        self.broker_port = broker_port
        self.max_retries = max_retries
        self._connected = False

        # Configure security based on type
        if security in ["username", "tls_with_client_cert"]:
            if not auth or not auth.get("username") or not auth.get("password"):
                raise ValueError("Username/password required but not provided")
            self.client.username_pw_set(auth["username"], auth["password"])

        if security in ["tls", "tls_with_client_cert"] and tls:
            try:
                self.client.tls_set(
                    ca_certs=tls.get("ca_cert"),
                    certfile=tls.get("client_cert"),
                    keyfile=tls.get("client_key"),
                    cert_reqs=ssl.CERT_REQUIRED if tls.get("verify") else ssl.CERT_NONE,
                    tls_version=ssl.PROTOCOL_TLS,
                )
                self.client.tls_insecure_set(not tls.get("verify", True))
            except Exception as e:
                print(f"TLS setup failed: {e}")
                raise

        # Set up callbacks
        self.client.on_connect = self._on_connect
        self.client.on_disconnect = self._on_disconnect

    def _on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            self._connected = True
            print("Connected to MQTT broker")
        else:
            print(f"Connection failed with code {rc}")

    def _on_disconnect(self, client, userdata, rc):
        self._connected = False
        if rc != 0:
            print(f"Unexpected disconnection {rc}")

    def connect(self) -> bool:
        """Connect to the MQTT broker with retry logic."""
        retries = 0
        while retries < self.max_retries:
            try:
                print(f"Attempting connection to {self.broker_url}:{self.broker_port}")
                self.client.connect(self.broker_url, self.broker_port, keepalive=60)
                self.client.loop_start()
                # Wait for connection
                timeout = 5
                start_time = time.time()
                while not self._connected and (time.time() - start_time) < timeout:
                    time.sleep(0.1)
                if self._connected:
                    return True
                print("Connection timeout")
            except Exception as e:
                print(f"Connection attempt {retries + 1} failed: {e}")
                retries += 1
                if retries < self.max_retries:
                    time.sleep(2)  # Wait before retry
        return False

    def disconnect(self) -> None:
        """Disconnect from the MQTT broker."""
        if self._connected:
            self.client.loop_stop()
            self.client.disconnect()
            self._connected = False

    def publish(
        self, topic: str, payload: Any, qos: int = 0, retain: bool = False
    ) -> bool:
        """Publish a payload to a topic."""
        if not self._connected:
            print("Not connected to broker")
            return False

        try:
            # Automatically serialize dicts/lists to JSON
            if isinstance(payload, (dict, list)):
                payload = json.dumps(payload)

            result = self.client.publish(topic, payload, qos, retain)
            return result.rc == mqtt.MQTT_ERR_SUCCESS
        except Exception as e:
            print(f"Publication failed: {e}")
            return False

    def __enter__(self):
        if not self.connect():
            raise ConnectionError("Failed to connect to MQTT broker")
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.disconnect()
