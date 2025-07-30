import os
import yaml
from functools import reduce
import operator
from typing import Optional, Any


class Config:
    """
    Handles loading and accessing configuration from a YAML file.
    """

    def __init__(self, config_path: Optional[str] = None, config_data: Optional[dict] = None):
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
                with open(self.config_path, 'r') as config_file:
                    loaded_config = yaml.safe_load(config_file)
                    # Ensure config is a dictionary even if the file is empty
                    if isinstance(loaded_config, dict):
                        self.config = loaded_config
            except FileNotFoundError:
                # If the file doesn't exist, self.config remains {}
                pass
        else:
            raise ValueError(
                "Either config_path or config_data must be provided.")

    def get(self, key: str, default: Any = None) -> Any:
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
