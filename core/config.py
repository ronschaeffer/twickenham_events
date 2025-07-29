import os
import yaml
from functools import reduce
import operator


class Config:
    """
    Handles loading and accessing configuration from a YAML file.
    """

    def __init__(self, config_path: str):
        """
        Initializes the Config object.

        Args:
            config_path (str): The absolute path to the configuration YAML file.
        """
        self.config_path = os.path.abspath(config_path)
        self.config_dir = os.path.dirname(self.config_path)
        self.config = {}  # Default to an empty config

        try:
            with open(self.config_path, 'r') as config_file:
                loaded_config = yaml.safe_load(config_file)
                # Ensure config is a dictionary even if the file is empty
                if isinstance(loaded_config, dict):
                    self.config = loaded_config
        except FileNotFoundError:
            # If the file doesn't exist, self.config remains {}
            pass

    def get(self, key: str, default=None):
        """
        Retrieve a value from the configuration using dot notation.
        If a key is not found, or its value is None, the default is returned.

        Args:
            key (str): The key to retrieve, e.g., 'mqtt.broker.host'.
            default: The value to return if the key is not found or is None.

        Returns:
            The value from the configuration or the default.
        """
        keys = key.split('.')
        try:
            # Traverse the nested dictionaries using the keys
            value = reduce(operator.getitem, keys, self.config)
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

