from functools import reduce
import operator
import os
from typing import Any, Dict, Optional  # noqa: UP035

import yaml


class Config:
    """
    Handles loading and accessing configuration from a YAML file.
    """

    def __init__(
        self, config_path: Optional[str] = None, config_data: Optional[dict] = None
    ):
        """
        Initializes the Config object.

        Can be initialized either by providing a path to a YAML file or by
        passing a dictionary directly.

        Args:
            config_path (str, optional): The absolute path to the configuration YAML file.
            config_data (dict, optional): A dictionary containing the configuration.
        """
        if config_data is not None:
            self.config = config_data
            self.config_path = None
            self.config_dir = os.getcwd()  # Default to current dir when no path
        elif config_path:
            self.config_path = os.path.abspath(config_path)
            self.config_dir = os.path.dirname(self.config_path)
            self.config = {}  # Default to an empty config

            try:
                with open(self.config_path) as config_file:
                    loaded_config = yaml.safe_load(config_file)
                    # Ensure config is a dictionary even if the file is empty
                    if isinstance(loaded_config, dict):
                        self.config = loaded_config
            except FileNotFoundError:
                # If the file doesn't exist, self.config remains {}
                pass
        else:
            raise ValueError("Either config_path or config_data must be provided.")

    def get(self, key: str, default: Any = None) -> Any:
        """
        Retrieve a value from the configuration using dot notation.
        If a key is not found, or its value is None, the default is returned.
        Supports environment variable substitution using ${VAR} syntax.
        Automatically handles type conversion for common cases.

        Args:
            key (str): The key to retrieve, e.g., 'mqtt.broker.host'.
            default: The value to return if the key is not found or is None.

        Returns:
            The value from the configuration or the default.
        """
        keys = key.split(".")
        try:
            # Traverse the nested dictionaries using the keys
            value = reduce(operator.getitem, keys, self.config)

            # Handle environment variable substitution for string values
            if (
                isinstance(value, str)
                and value.startswith("${")
                and value.endswith("}")
            ):
                env_var = value[2:-1]  # Remove ${ and }
                env_value = os.environ.get(env_var)
                if env_value is not None:
                    value = env_value
                else:
                    # If environment variable is not set, return default or the original value
                    return default if default is not None else value

            # Auto-convert port numbers to integers if the key suggests it's a port
            if isinstance(value, str) and "port" in key.lower():
                try:
                    value = int(value)
                except ValueError:
                    pass  # Keep as string if conversion fails

            # Return the value only if it's not None, otherwise return default
            return value if value is not None else default
        except (KeyError, TypeError):
            # This catches cases where a key doesn't exist or the path is invalid
            return default

    def get_config_dir(self) -> str:
        """
        Returns the directory where the configuration file is located.
        """
        return self.config_dir

    def get_mqtt_config(self) -> Dict[str, Any]:  # noqa: UP006
        """
        Build MQTT configuration dictionary with enhanced validation and type conversion.
        Handles individual access for proper environment variable substitution.

        Returns:
            dict: MQTT configuration ready for MQTTPublisher initialization

        Raises:
            ValueError: If required configuration is missing or invalid
        """
        # Handle port conversion with proper validation
        raw_port = self.get("mqtt.broker_port", 1883)
        try:
            broker_port = int(raw_port) if raw_port is not None else 1883
        except (ValueError, TypeError) as e:
            raise ValueError(f"MQTT broker_port '{raw_port}' must be 1-65535") from e

        if not (1 <= broker_port <= 65535):
            raise ValueError(f"MQTT broker_port {broker_port} must be 1-65535")

        # Handle max_retries conversion with proper defaults
        raw_retries = self.get("mqtt.max_retries", 3)
        max_retries = int(raw_retries) if raw_retries is not None else 3

        config = {
            "broker_url": self.get("mqtt.broker_url"),
            "broker_port": broker_port,
            "client_id": self.get("mqtt.client_id", "twickenham_event_publisher"),
            "security": self.get("mqtt.security", "none"),
            "auth": {
                "username": self.get("mqtt.auth.username"),
                "password": self.get("mqtt.auth.password"),
            },
            "tls": self.get("mqtt.tls"),
            "max_retries": max_retries,
        }

        # Validate required fields
        if not config["broker_url"]:
            raise ValueError("MQTT broker_url is required but not configured")

        return config
