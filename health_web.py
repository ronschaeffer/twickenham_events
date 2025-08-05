#!/usr/bin/env python3
"""
Simple HTTP health endpoint for external monitoring
Run with: poetry run python health_web.py
"""

import json
from pathlib import Path
import subprocess

from flask import Flask, jsonify

app = Flask(__name__)


@app.route("/health")
def health():
    """Health check endpoint for Uptime Kuma and other monitors."""
    try:
        # Run health check
        project_root = Path(__file__).parent
        result = subprocess.run(
            ["poetry", "run", "python", "-m", "core.health_check"],
            capture_output=True,
            text=True,
            cwd=str(project_root),
            timeout=30,
        )

        if result.stdout:
            health_data = json.loads(result.stdout)
        else:
            health_data = {
                "status": "error",
                "error": "No output from health check",
                "stderr": result.stderr,
            }

        # Return appropriate HTTP status
        if result.returncode == 0:
            return jsonify(health_data), 200  # Healthy
        elif result.returncode == 2:
            return jsonify(health_data), 200  # Warning but still OK
        else:
            return jsonify(health_data), 503  # Service unavailable

    except subprocess.TimeoutExpired:
        return jsonify(
            {"status": "error", "error": "Health check timeout"}
        ), 508  # Loop detected (timeout)

    except Exception as e:
        return jsonify(
            {"status": "error", "error": str(e)}
        ), 500  # Internal server error


@app.route("/ping")
def ping():
    """Simple ping endpoint."""
    return jsonify({"status": "ok", "message": "pong"}), 200


if __name__ == "__main__":
    print("🏥 Starting Twickenham Events Health Web Server")
    print("📊 Health endpoint: http://localhost:8080/health")
    print("🏓 Ping endpoint: http://localhost:8080/ping")
    app.run(host="0.0.0.0", port=8080, debug=False)
