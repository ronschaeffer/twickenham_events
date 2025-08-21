#!/usr/bin/env python3
"""
Configuration Validation Script for Twickenham Events

This script validates environment variables in .env against config.yaml references
and checks for proper formatting and consistency.

Usage:
    python validate_config.py
    # or from project root:
    python scripts/validate_config.py
"""

from pathlib import Path
import re
import sys


def load_env_file(env_path=".env"):
    """Load environment variables from .env file."""
    env_vars = {}
    if Path(env_path).exists():
        with open(env_path) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, value = line.split("=", 1)
                    env_vars[key.strip()] = value.strip()
    return env_vars


def load_config_references(config_path="config/config.yaml"):
    """Load variable references from config.yaml."""
    config_vars = {}
    if Path(config_path).exists():
        with open(config_path) as f:
            content = f.read()
            # Find all ${VARIABLE} references
            var_refs = re.findall(r'"?\${([^}]+)}"?', content)
            for var in var_refs:
                config_vars[var] = True
    return config_vars


def validate_boolean(key, value):
    """Validate boolean environment variables."""
    valid_bools = {"true", "false", "1", "0", "yes", "no", "on", "off"}
    if value.lower() not in valid_bools:
        return f"❌ {key}={value} (should be true/false)"
    return f"✅ {key}={value}"


def validate_port(key, value):
    """Validate port number environment variables."""
    try:
        port = int(value)
        if 1 <= port <= 65535:
            return f"✅ {key}={value} (valid port)"
        else:
            return f"❌ {key}={value} (port out of range 1-65535)"
    except ValueError:
        return f"❌ {key}={value} (not a valid port number)"


def validate_url(key, value):
    """Validate URL environment variables."""
    if value.startswith(("http://", "https://")):
        return f"✅ {key}={value} (valid URL)"
    return f"⚠️  {key}={value} (should start with http:// or https://)"


def validate_host(key, value):
    """Validate host/IP environment variables."""
    if value in ["0.0.0.0", "127.0.0.1", "localhost"] or re.match(
        r"^\d+\.\d+\.\d+\.\d+$", value
    ):
        return f"✅ {key}={value} (valid host)"
    return f"⚠️  {key}={value} (should be IP address or hostname)"


def validate_security_mode(key, value):
    """Validate MQTT security mode."""
    valid_modes = {"none", "username", "cert", "username_cert"}
    if value.lower() in valid_modes:
        return f"✅ {key}={value} (valid security mode)"
    return f"❌ {key}={value} (should be: none, username, cert, or username_cert)"


def main():
    """Main validation function."""
    print("🔍 === Twickenham Events Configuration Validator ===")
    print("Checking .env file and config.yaml for consistency and validity\n")

    # Load configuration files
    env_vars = load_env_file()
    config_vars = load_config_references()

    print(f"📄 Found {len(env_vars)} variables in .env")
    print(f"📄 Found {len(config_vars)} variable references in config.yaml\n")

    # Define validation rules
    validators = {
        # Boolean variables
        "MQTT_ENABLED": validate_boolean,
        "HOME_ASSISTANT_ENABLED": validate_boolean,
        "CALENDAR_ENABLED": validate_boolean,
        "TYPE_DETECTION_ENABLED": validate_boolean,
        "SHORTENING_ENABLED": validate_boolean,
        "FLAGS_ENABLED": validate_boolean,
        "WEB_SERVER_ENABLED": validate_boolean,
        "WEB_SERVER_ACCESS_LOG": validate_boolean,
        "WEB_SERVER_CORS_ENABLED": validate_boolean,
        "TLS_VERIFY": validate_boolean,
        # Port variables
        "MQTT_BROKER_PORT": validate_port,
        "WEB_SERVER_PORT": validate_port,
        # URL variables
        "WEB_SERVER_EXTERNAL_URL": validate_url,
        # Host variables
        "WEB_SERVER_HOST": validate_host,
        "MQTT_BROKER_URL": validate_host,
        # Security mode
        "MQTT_SECURITY": validate_security_mode,
    }

    # Validate environment variables
    print("📋 === Environment Variable Validation ===")
    validation_results = []
    for key, value in sorted(env_vars.items()):
        if key in validators:
            result = validators[key](key, value)
            validation_results.append(result)
            print(f"   {result}")
        else:
            print(f"   i  {key}={value} (no specific validation)")

    # Check config references
    print("\n🔗 === Config.yaml Reference Check ===")
    missing_in_env = []
    for var in sorted(config_vars.keys()):
        if var in env_vars:
            print(f"   ✅ {var} (defined in .env)")
        else:
            missing_in_env.append(var)
            print(f"   ❌ {var} (referenced in config.yaml but missing from .env)")

    # Generate summary
    print("\n📊 === Summary ===")
    error_count = len([r for r in validation_results if "❌" in r])
    warning_count = len([r for r in validation_results if "⚠️" in r])
    success_count = len([r for r in validation_results if "✅" in r])

    print(f"✅ {success_count} settings valid")
    print(f"⚠️  {warning_count} settings have warnings")
    print(f"❌ {error_count} settings have errors")
    print(f"❌ {len(missing_in_env)} variables missing from .env")

    # Show missing variables
    if missing_in_env:
        print("\n🔧 === Missing Variables ===")
        for var in missing_in_env:
            print(f"   Add to .env: {var}=<value>")

    # Component-specific checks
    print("\n💡 === Component Status ===")

    # Web Server Check
    if env_vars.get("WEB_SERVER_ENABLED", "").lower() == "true":
        print("🌐 Web Server: ENABLED")
        required_web_vars = [
            "WEB_SERVER_HOST",
            "WEB_SERVER_PORT",
            "WEB_SERVER_EXTERNAL_URL",
        ]
        web_ready = all(var in env_vars for var in required_web_vars)
        print(
            f"   {'✅' if web_ready else '❌'} Configuration {'complete' if web_ready else 'incomplete'}"
        )
    else:
        print("🌐 Web Server: DISABLED")

    # MQTT Check
    if env_vars.get("MQTT_ENABLED", "").lower() == "true":
        print("📡 MQTT: ENABLED")
        required_mqtt_vars = ["MQTT_BROKER_URL", "MQTT_BROKER_PORT", "MQTT_CLIENT_ID"]
        mqtt_ready = all(var in env_vars for var in required_mqtt_vars)
        print(
            f"   {'✅' if mqtt_ready else '❌'} Configuration {'complete' if mqtt_ready else 'incomplete'}"
        )
    else:
        print("📡 MQTT: DISABLED")

    # AI Processing Check
    if (
        env_vars.get("TYPE_DETECTION_ENABLED", "").lower() == "true"
        or env_vars.get("SHORTENING_ENABLED", "").lower() == "true"
    ):
        print("🤖 AI Processing: ENABLED")
        ai_ready = "GEMINI_API_KEY" in env_vars
        print(
            f"   {'✅' if ai_ready else '❌'} API Key {'configured' if ai_ready else 'missing'}"
        )
    else:
        print("🤖 AI Processing: DISABLED")

    # Final status
    print("\n🎯 === Final Status ===")
    if error_count == 0 and len(missing_in_env) == 0:
        print("🎉 All settings are valid and consistent!")
        return 0
    else:
        print("📝 Review and fix the issues above before deployment")
        return 1


if __name__ == "__main__":
    sys.exit(main())
