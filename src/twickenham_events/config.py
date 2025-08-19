"""
Configuration management for Twickenham Events.

Provides a modern, type-safe configuration system with validation.
"""

import os
from pathlib import Path
from typing import Any, Optional

from dotenv import dotenv_values
import yaml

# Lazy one-time .env loading flag
_ENV_LOADED = False


def _load_env_once() -> None:
    global _ENV_LOADED
    if _ENV_LOADED:
        return
    # Load environment files with cascading precedence:
    # 1) system environment (highest) - already present in os.environ
    # 2) project-level .env (overrides workspace defaults)
    # 3) workspace-level .env (defaults for all projects)
    # Implementation: read both files, merge (project overrides workspace) and
    # set values into os.environ only when the key is not already present in
    # the system environment. This prevents accidental overwriting of OS envs.
    project_root = Path(__file__).parent.parent.parent
    workspace_env = project_root.parent / ".env"
    project_env = project_root / ".env"

    # Read dotenv files into dictionaries (no side-effects)
    workspace_vals = dotenv_values(workspace_env) if workspace_env.exists() else {}
    project_vals = dotenv_values(project_env) if project_env.exists() else {}

    # Merge: project values override workspace defaults
    merged = {}
    merged.update({k: v for k, v in workspace_vals.items() if v is not None})
    merged.update({k: v for k, v in project_vals.items() if v is not None})

    # Apply merged values to environment only when not already defined by OS
    for k, v in merged.items():
        if k and v is not None and k not in os.environ:
            os.environ[k] = str(v)
    _ENV_LOADED = True


class Config:
    """Configuration manager with validation and defaults."""

    config_path: Optional[str] = None

    def __init__(self, config_data: dict):
        _load_env_once()
        """Initialize configuration from dictionary."""
        self._data = config_data
        # Instance-specific path; may be set by from_file or from_defaults
        self.config_path = None

    @classmethod
    def from_file(cls, config_path: str) -> "Config":
        _load_env_once()
        """Load configuration from YAML file."""
        path = Path(config_path)

        if not path.exists():
            # Try relative to project root
            project_root = Path(__file__).parent.parent.parent
            path = project_root / config_path

            if not path.exists():
                raise FileNotFoundError(f"Configuration file not found: {config_path}")

        with open(path) as f:
            data = yaml.safe_load(f)

        instance = cls(data)
        instance.config_path = str(path)
        return instance

    @classmethod
    def from_defaults(cls) -> "Config":
        _load_env_once()
        """Create configuration with default values."""
        defaults = {
            "scraping": {
                "url": "https://www.twickenham-stadium.com/fixtures-and-events",
                "timeout": 30,
                "retries": 3,
            },
            "service": {
                "interval_seconds": 14400,  # 4 hours
                "enable_buttons": True,
                "discovery_prefix": "homeassistant",
                "systemd": {
                    "auto_launch": False,
                    "unit": "twickenham-events.service",
                    "user": True,
                    "delay_seconds": 2,
                },
            },
            "mqtt": {
                "enabled": False,
                "broker": "localhost",
                "port": 1883,
                "tls": False,
                "topics": {
                    "all_upcoming": "twickenham_events/events/all_upcoming",
                    "next": "twickenham_events/events/next",
                    "status": "twickenham_events/status",
                },
            },
            "calendar": {"enabled": True, "filename": "twickenham_events.ics"},
            "ai_processor": {
                "api_key": "${GEMINI_API_KEY}",
                "type_detection": {
                    "enabled": False,
                    "cache_enabled": True,
                    "cache_dir": "output/cache",
                    "model": "gemini-2.5-pro",
                },
                "shortening": {
                    "enabled": False,
                    "cache_enabled": True,
                    "model": "gemini-2.5-pro",
                    "max_length": 16,
                    "retry_minutes_on_quota": 10,
                    "flags_enabled": False,
                    "standardize_spacing": True,
                    "prompt_template": "",
                },
            },
            "web_server": {"enabled": False, "host": "0.0.0.0", "port": 8080},
        }

        instance = cls(defaults)
        instance.config_path = "defaults"
        return instance

    def get(self, key: str, default: Any = None) -> Any:
        """Get configuration value using dot notation."""
        keys = key.split(".")
        value = self._data

        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default

        # Environment variable override
        env_key = f"TWICK_{key.upper().replace('.', '_')}"
        env_value = os.getenv(env_key)
        if env_value is not None:
            # Basic type conversion
            if isinstance(value, bool):
                return env_value.lower() in ("true", "1", "yes", "on")
            elif isinstance(value, int):
                try:
                    return int(env_value)
                except ValueError:
                    pass
            elif isinstance(value, float):
                try:
                    return float(env_value)
                except ValueError:
                    pass
            return env_value

        # Handle ${VARIABLE} expansion in string values
        if isinstance(value, str) and value.startswith("${") and value.endswith("}"):
            env_var = value[2:-1]  # Remove ${ and }
            expanded_value = os.getenv(env_var)
            if expanded_value is not None:
                return expanded_value
            # If env var not found, return the original value (so it fails gracefully)

        return value

    @property
    def scraping_url(self) -> str:
        """Get scraping URL."""
        return self.get("scraping.url", "")

    @property
    def scraping_timeout(self) -> int:
        """Get scraping timeout."""
        return self.get("scraping.timeout", 30)

    @property
    def scraping_retries(self) -> int:
        """Get scraping retries."""
        return self.get("scraping.retries", 3)

    @property
    def mqtt_enabled(self) -> bool:
        """Check if MQTT is enabled."""
        return self.get("mqtt.enabled", False)

    @property
    def mqtt_broker(self) -> str:
        """Get MQTT broker."""
        # Support both new style (broker_url) and legacy (broker) keys, plus env overrides.
        primary = self.get("mqtt.broker_url", None)
        legacy = self.get("mqtt.broker", None)
        val = primary or legacy or "localhost"
        # Handle unexpanded ${VAR} placeholders by falling back to legacy or default
        if isinstance(val, str) and val.startswith("${"):
            val = legacy if legacy and not str(legacy).startswith("${") else "localhost"
        # Ensure we return a string for mqtt broker
        return str(val)

    @property
    def mqtt_port(self) -> int:
        """Get MQTT port."""
        # Support both new style (broker_port) and legacy (port) keys.
        primary = self.get("mqtt.broker_port", None)
        legacy = self.get("mqtt.port", None)
        val = primary if primary is not None else legacy
        if val is None:
            return 1883
        if isinstance(val, str):
            if val.startswith("${") or not val.strip():
                # Try legacy if primary was placeholder
                if legacy and not str(legacy).startswith("${"):
                    val = legacy
                else:
                    return 1883
            try:
                return int(val)
            except ValueError:
                return 1883
        try:
            return int(val)
        except Exception:
            return 1883

    @property
    def mqtt_tls(self) -> bool:
        """Check if MQTT TLS is enabled."""
        return self.get("mqtt.tls", False)

    @property
    def mqtt_username(self) -> Optional[str]:
        """Get MQTT username."""
        return self.get("mqtt.auth.username")

    @property
    def mqtt_password(self) -> Optional[str]:
        """Get MQTT password."""
        return self.get("mqtt.auth.password")

    @property
    def mqtt_client_id(self) -> str:
        """Get MQTT client ID."""
        return self.get("mqtt.client_id", "twickenham_events")

    @property
    def calendar_enabled(self) -> bool:
        """Check if calendar is enabled."""
        return self.get("calendar.enabled", True)

    @property
    def calendar_filename(self) -> str:
        """Get calendar filename."""
        return self.get("calendar.filename", "twickenham_events.ics")

    @property
    def ai_enabled(self) -> bool:
        """Check if AI processor shortening is enabled."""
        return self.get("ai_processor.shortening.enabled", False)

    @property
    def ai_model(self) -> str:
        """Get AI model for shortening."""
        return self.get("ai_processor.shortening.model", "gemini-2.5-pro")

    @property
    def ai_max_length(self) -> int:
        """Get AI max length for shortening."""
        return self.get("ai_processor.shortening.max_length", 16)

    @property
    def ai_api_key(self) -> Optional[str]:
        """Get AI API key."""
        return self.get("ai_processor.api_key") or os.getenv("GEMINI_API_KEY")

    @property
    def web_enabled(self) -> bool:
        """Check if web server is enabled."""
        return self.get("web_server.enabled", False)

    @property
    def web_host(self) -> str:
        """Get web server host."""
        return self.get("web_server.host", "0.0.0.0")

    @property
    def web_port(self) -> int:
        """Get web server port."""
        return self.get("web_server.port", 8080)

    # Service (daemon) settings
    @property
    def service_interval_seconds(self) -> int:
        return int(self.get("service.interval_seconds", 14400))

    @property
    def service_buttons_enabled(self) -> bool:
        return self.get("service.enable_buttons", True)

    @property
    def service_discovery_prefix(self) -> str:
        return self.get("service.discovery_prefix", "homeassistant")

    def get_mqtt_topics(self) -> dict:
        """Get MQTT topics configuration."""
        return self.get("mqtt.topics", {})

    def get_mqtt_config(self) -> dict:
        """Get complete MQTT configuration for MQTTPublisher (ha-mqtt-publisher)."""
        # If this Config object was created directly from a dict (i.e. via
        # Config(config_data=...)) we require the caller to provide an explicit
        # MQTT broker (either 'broker_url' or legacy 'broker') so that tests and
        # callers who construct Config programmatically get a clear failure
        # rather than silently falling back to localhost.
        mqtt_section = (
            self._data.get("mqtt", {}) if isinstance(self._data, dict) else {}
        )
        if self.config_path is None and not (
            mqtt_section.get("broker_url") or mqtt_section.get("broker")
        ):
            raise ValueError("broker_url is required")

        cfg = {
            "broker_url": self.mqtt_broker,
            "broker_port": self.mqtt_port,
            "client_id": self.mqtt_client_id,
            "security": self.get("mqtt.security", "none"),
            "max_retries": self.get("mqtt.max_retries", 3),
        }
        tls_cfg = self.get("mqtt.tls")
        # Allow several forms to enable TLS:
        # - a dict in config (detailed TLS settings)
        # - a boolean True in config
        # - an environment variable MQTT_USE_TLS set to true/1/yes
        if isinstance(tls_cfg, dict):  # allow dict TLS settings
            # If dict is empty, default to permissive verification False to allow
            # local validation without CA certs. Production should set 'verify: True'.
            if tls_cfg:
                cfg["tls"] = tls_cfg
            else:
                cfg["tls"] = {"verify": False}
        else:
            # Interpret explicit boolean True from YAML
            if isinstance(tls_cfg, bool) and tls_cfg:
                cfg["tls"] = {"verify": False}
            else:
                # Fall back to env var MQTT_USE_TLS if present
                env_tls = os.getenv("MQTT_USE_TLS")
                if env_tls is not None and str(env_tls).lower() in (
                    "true",
                    "1",
                    "yes",
                    "on",
                ):
                    # Enable TLS. If no TLS details provided, default to a permissive
                    # mode (verify=False) to simplify local validation runs where no
                    # CA certificate has been configured. Users should supply
                    # CA/client certs in production.
                    cfg["tls"] = {"verify": False}
        if cfg["security"] == "username" and self.mqtt_username and self.mqtt_password:
            cfg["auth"] = {
                "username": self.mqtt_username,
                "password": self.mqtt_password,
            }
        last_will = self.get("mqtt.last_will")
        if isinstance(last_will, dict):
            cfg["last_will"] = last_will
        return cfg
