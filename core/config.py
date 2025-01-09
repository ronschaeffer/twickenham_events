import os
import yaml

class Config:
    def __init__(self, config_path):
        with open(config_path, 'r') as config_file:
            self.config = yaml.safe_load(config_file)

    def __getattr__(self, name):
        # First try to get directly from top level
        if name in self.config:
            return self.config[name]

        # If not found, try nested dictionary lookup
        keys = name.split('_')
        value = self.config
        for key in keys:
            if not isinstance(value, dict) or key not in value:
                raise AttributeError(f"Configuration key '{name}' not found")
            value = value[key]
        return value

    def get(self, name, default=None):
        try:
            return self.__getattr__(name)
        except AttributeError:
            return default