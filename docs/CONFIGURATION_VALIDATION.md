# Configuration Validation

This document explains how to use the configuration validation script to ensure your environment variables and configuration files are properly set up.

## Quick Validation

Run the validation script from the project root:

```bash
python scripts/validate_config.py
```

## What It Checks

### ✅ **Environment Variable Validation**
- **Boolean values**: Checks that true/false settings use valid values
- **Port numbers**: Validates port ranges (1-65535)
- **URLs**: Ensures proper http:// or https:// format
- **Host addresses**: Validates IP addresses and hostnames
- **Security modes**: Checks MQTT security configuration

### 🔗 **Configuration Consistency**
- Compares `.env` file against `config.yaml` references
- Identifies missing environment variables
- Reports unused environment variables

### 🎯 **Component Status**
- **Web Server**: Checks if all required variables are present
- **MQTT**: Validates broker connection settings
- **AI Processing**: Verifies API key configuration

## Current Status Summary

Based on your latest validation:

### ✅ **Working Components**
- **Web Server**: ✅ Fully configured and ready
  - `WEB_SERVER_ENABLED=true`
  - `WEB_SERVER_HOST=0.0.0.0`
  - `WEB_SERVER_PORT=47476`
  - `WEB_SERVER_EXTERNAL_URL=http://10.10.10.20:47476`

### ❌ **Components Needing Configuration**

#### MQTT Integration
Missing required variables:
```bash
MQTT_BROKER_URL=<your_mqtt_broker_ip>
MQTT_BROKER_PORT=1883
MQTT_USERNAME=<your_username>
MQTT_PASSWORD=<your_password>
MQTT_SECURITY=username
TLS_VERIFY=false
```

#### AI Processing
Missing API key:
```bash
GEMINI_API_KEY=<your_google_gemini_api_key>
```

#### Optional TLS Certificates
Only needed if using TLS with MQTT:
```bash
TLS_CA_CERT=<path_to_ca_cert>
TLS_CLIENT_CERT=<path_to_client_cert>
TLS_CLIENT_KEY=<path_to_client_key>
```

## Quick Setup Guide

### 1. **Web Server Only** (Currently Working!)
Your web server is ready to run. No additional configuration needed.

### 2. **Add MQTT Integration**
To enable Home Assistant integration, add these to your `.env`:

```bash
# Add to .env file
MQTT_BROKER_URL=10.10.10.20  # Your MQTT broker IP
MQTT_BROKER_PORT=1883
MQTT_USERNAME=homeassistant
MQTT_PASSWORD=your_password
MQTT_SECURITY=username
TLS_VERIFY=false
```

### 3. **Add AI Features**
To enable event name shortening and type detection:

```bash
# Add to .env file
GEMINI_API_KEY=your_google_gemini_api_key
```

## Validation Output Explained

### Status Icons
- ✅ **Valid**: Setting is correctly formatted and ready to use
- ⚠️ **Warning**: Setting works but may need attention
- ❌ **Error**: Setting has problems that need fixing
- `i` **Info**: Setting found but no specific validation rules

### Component Status
- **ENABLED**: Component is turned on in configuration
- **DISABLED**: Component is turned off
- **Configuration complete**: All required variables present
- **Configuration incomplete**: Missing required variables

## Troubleshooting

### "Configuration incomplete" Messages
This means you're missing required environment variables for that component. Add the missing variables to your `.env` file.

### Validation Errors
Check the specific error message and fix the format:
- Boolean values: Use `true` or `false`
- Ports: Use numbers between 1-65535
- URLs: Start with `http://` or `https://`

### Missing Variables
The script will list exactly which variables to add to your `.env` file.

## Next Steps

1. **Run validation**: `python scripts/validate_config.py`
2. **Fix any errors**: Update your `.env` file based on the output
3. **Add missing components**: Configure MQTT and/or AI features as needed
4. **Re-run validation**: Confirm everything is working
5. **Start the application**: Your configuration is ready!

Your web server configuration is already perfect - you can start using that immediately! 🚀
